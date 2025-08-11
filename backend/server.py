from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import json
import httpx
import networkx as nx


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Groq API configuration
GROQ_API_KEY = os.environ['GROQ_API_KEY']
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class ProjectInput(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    objective: str
    deadline: Optional[str] = None
    budget: Optional[float] = None
    tech_stack: Optional[str] = None
    team_size: Optional[str] = None
    complexity: Optional[str] = "medium"
    deliverables: Optional[List[str]] = []
    constraints: Optional[Dict[str, Any]] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    current_step: str = "greeting"
    completed_steps: List[str] = []
    context: Dict[str, Any] = {}
    messages: List[Dict[str, str]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskEstimate(BaseModel):
    id: str
    title: str
    description: str
    category: Optional[str] = "General"
    acceptance_criteria: List[str]
    dependencies: List[str]
    roles: List[Dict[str, Any]]
    optimistic_days: float
    most_likely_days: float
    pessimistic_days: float
    expected_days: float
    risk: str = "medium"
    priority: Optional[str] = "medium"

class ProjectEstimate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    tasks: List[TaskEstimate]
    total_cost: float
    total_duration_days: float
    critical_path: List[str]
    start_date: str
    end_date: str
    resource_allocation: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Default hourly rates (in INR)
DEFAULT_RATES = {
    "Junior Developer": 400,
    "Mid Developer": 800,
    "Senior Developer": 1500,
    "Architect": 2500,
    "QA Engineer": 600,
    "Project Manager": 1800,
    "UI/UX Designer": 1200,
    "DevOps Engineer": 1800
}

# Groq client
async def call_groq_api(messages, system_prompt="You are an expert IT project estimator."):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt}
                ] + messages,
                "model": "openai/gpt-oss-20b",
                "temperature": 0.7,
                "max_completion_tokens": 4096,
                "top_p": 1,
                "stream": False
            }
            
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise HTTPException(status_code=500, detail=f"Groq API error: {response.text}")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calling Groq API: {str(e)}")

# Helper functions
def calculate_pert_estimate(optimistic: float, most_likely: float, pessimistic: float) -> float:
    """Calculate PERT expected duration"""
    return (optimistic + 4 * most_likely + pessimistic) / 6

def calculate_critical_path(tasks: List[Dict], dependencies: Dict[str, List[str]]) -> List[str]:
    """Calculate critical path using NetworkX"""
    G = nx.DiGraph()
    
    # Add nodes with durations
    for task in tasks:
        G.add_node(task["id"], duration=task["expected_days"])
    
    # Add edges for dependencies
    for task_id, deps in dependencies.items():
        for dep in deps:
            G.add_edge(dep, task_id)
    
    # Calculate critical path (longest path)
    try:
        critical_path = nx.dag_longest_path(G, weight='duration')
        return critical_path
    except:
        return []

async def decompose_project_with_groq(project_data: dict) -> dict:
    """Use Groq to decompose project into tasks"""
    system_prompt = """You are an expert IT project estimator with deep knowledge of software development lifecycles. Decompose projects into comprehensive, detailed tasks across ALL development domains.

MANDATORY TASK CATEGORIES TO INCLUDE:

**1. PROJECT PLANNING & ANALYSIS**
- Requirements gathering and analysis
- Technical specification documentation
- Project architecture planning
- Risk assessment and mitigation planning
- Resource allocation and team planning

**2. FRONTEND DEVELOPMENT (Detailed)**
- UI/UX Design System implementation
- Component library development (reusable components)
- Responsive design implementation (mobile, tablet, desktop)
- State management setup (Redux/Context API)
- API integration and data fetching
- Form validation and user input handling
- Client-side routing implementation
- Performance optimization (lazy loading, code splitting)
- Cross-browser compatibility testing
- Accessibility (WCAG 2.1 compliance) implementation
- Frontend unit and integration testing
- Progressive Web App (PWA) features if applicable

**3. BACKEND DEVELOPMENT (Detailed)**
- Database schema design and modeling
- RESTful API architecture and endpoints
- Authentication and authorization systems
- Business logic implementation
- Data validation and sanitization
- Error handling and logging systems
- API rate limiting and throttling
- File upload and storage management
- Email/SMS notification systems
- Background job processing (if needed)
- API documentation (Swagger/OpenAPI)
- Backend unit and integration testing
- Performance optimization and caching

**4. DATABASE DESIGN & MANAGEMENT**
- Entity relationship design
- Database schema creation and migrations
- Index optimization for query performance
- Database connection pooling setup
- Data backup and recovery strategies
- Database security and access controls
- Data archiving and cleanup procedures
- Database monitoring and performance tuning
- Data import/export functionality

**5. SECURITY IMPLEMENTATION**
- Authentication system (JWT, OAuth, etc.)
- Authorization and role-based access control
- Data encryption (at rest and in transit)
- Input validation and sanitization
- SQL injection prevention
- Cross-Site Scripting (XSS) prevention
- Cross-Site Request Forgery (CSRF) protection
- Security headers implementation
- Vulnerability scanning and penetration testing
- GDPR/compliance requirements implementation
- Security audit and code review

**6. DEPLOYMENT & DEVOPS**
- Development environment setup
- Staging environment configuration
- Production environment setup
- CI/CD pipeline implementation
- Docker containerization
- Load balancing and auto-scaling setup
- SSL certificate installation and management
- Domain and DNS configuration
- Database backup automation
- Log aggregation and monitoring setup
- Performance monitoring and alerting
- Disaster recovery planning
- Documentation and runbooks

**7. TESTING & QUALITY ASSURANCE**
- Test plan development
- Unit testing implementation
- Integration testing
- End-to-end testing
- Performance testing and load testing
- Security testing
- User acceptance testing coordination
- Bug tracking and resolution
- Test automation setup

**8. PROJECT MANAGEMENT & DOCUMENTATION**
- Technical documentation creation
- User manual and API documentation
- Deployment documentation
- Code review processes
- Version control and branching strategies
- Knowledge transfer sessions
- Post-deployment support planning

Return ONLY valid JSON in this exact schema:
{
  "tasks": [
    {
      "id": "T1",
      "title": "Task name",
      "description": "Detailed description",
      "category": "Frontend Development|Backend Development|Database Design|Security|Deployment|Testing|Planning",
      "acceptance_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],
      "dependencies": ["T0"],
      "roles": [{"role": "Senior Developer", "hours_optimistic": 40, "hours_most_likely": 80, "hours_pessimistic": 120}],
      "optimistic_days": 5,
      "most_likely_days": 10,
      "pessimistic_days": 20,
      "risk": "low|medium|high",
      "priority": "high|medium|low"
    }
  ],
  "project_summary": {
    "total_estimated_days": 0,
    "complexity_assessment": "simple|medium|complex",
    "key_risks": ["Risk 1", "Risk 2"],
    "recommended_team_size": "3-5 developers",
    "critical_success_factors": ["Factor 1", "Factor 2"]
  }
}

ESTIMATION GUIDELINES:
- Frontend components: 2-8 days per major component
- API endpoints: 1-3 days per complex endpoint
- Database tables: 0.5-2 days per table with relationships
- Authentication system: 5-10 days total
- Security implementation: 3-15 days depending on requirements
- Deployment setup: 3-7 days
- Testing: 20-30% of development time
- Documentation: 10-15% of development time

DEPENDENCY RULES:
- Database schema must come before backend development
- Backend APIs must come before frontend integration
- Security implementation should be parallel to development
- Testing should follow each development phase
- Deployment preparation should start mid-project

Be extremely detailed and comprehensive. Include 25-40 tasks for complex projects."""

    messages = [
        {
            "role": "user", 
            "content": f"Project Details:\nName: {project_data.get('name', '')}\nObjective: {project_data.get('objective', '')}\nTech Stack: {project_data.get('tech_stack', 'Not specified')}\nComplexity: {project_data.get('complexity', 'medium')}\nDeliverables: {', '.join(project_data.get('deliverables', []))}\nDeadline: {project_data.get('deadline', 'Flexible')}\nBudget: {project_data.get('budget', 'Flexible')}"
        }
    ]
    
    response = await call_groq_api(messages, system_prompt)
    
    # Parse JSON response
    try:
        # Clean the response - remove markdown formatting if present
        clean_response = response.strip()
        if clean_response.startswith('```json'):
            clean_response = clean_response.replace('```json', '').replace('```', '').strip()
        
        parsed_data = json.loads(clean_response)
        return parsed_data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Groq response as JSON: {str(e)}")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "IT Project Planning Assistant API"}

@api_router.post("/chat/start")
async def start_conversation():
    """Start a new project planning conversation"""
    conversation = ConversationState(
        project_id=str(uuid.uuid4()),
        current_step="greeting",
        messages=[{
            "role": "assistant",
            "content": "Hi! I'm your IT Project Planning Assistant. I'll help you create detailed project estimates with timelines and costs. Let's start with your project basics:\n\n1. What's your project name?\n2. What's the main objective?\n3. Do you have a target deadline?"
        }]
    )
    
    # Save to database
    await db.conversations.insert_one(conversation.dict())
    return conversation

@api_router.post("/chat/{conversation_id}")
async def chat_response(conversation_id: str, message: dict):
    """Handle chat messages and guide conversation"""
    user_message = message.get("content", "")
    
    # Retrieve conversation
    conversation = await db.conversations.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Add user message
    conversation["messages"].append({"role": "user", "content": user_message})
    
    # Process based on current step
    current_step = conversation["current_step"]
    assistant_response = ""
    
    if current_step == "greeting":
        # Parse initial project info
        conversation["context"].update({
            "initial_input": user_message
        })
        conversation["current_step"] = "details"
        assistant_response = "Great! Now I need more details:\n\n1. What's your preferred tech stack?\n2. What's your team size preference?\n3. What are the key deliverables/features?\n4. What's your budget range?"
        
    elif current_step == "details":
        conversation["context"].update({
            "additional_details": user_message
        })
        conversation["current_step"] = "constraints"
        assistant_response = "Perfect! A few more questions:\n\n1. Any specific constraints or requirements?\n2. How would you rate the project complexity (simple/medium/complex)?\n3. Any existing assets or systems to integrate with?"
        
    elif current_step == "constraints":
        conversation["context"].update({
            "constraints": user_message
        })
        conversation["current_step"] = "ready_for_analysis"
        assistant_response = "Excellent! I have all the information needed. Let me analyze your project and create a detailed breakdown with tasks, timeline, and cost estimates. This will take a moment..."
        
    # Add assistant response
    conversation["messages"].append({"role": "assistant", "content": assistant_response})
    
    # Update conversation in database
    await db.conversations.replace_one({"id": conversation_id}, conversation)
    
    return {"response": assistant_response, "step": conversation["current_step"]}

@api_router.post("/analyze/{conversation_id}")
async def analyze_project(conversation_id: str):
    """Analyze project and generate estimates"""
    # Retrieve conversation
    conversation = await db.conversations.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Extract project data from conversation context
    context = conversation.get("context", {})
    project_data = {
        "name": "Project from conversation",
        "objective": context.get("initial_input", ""),
        "tech_stack": context.get("additional_details", ""),
        "complexity": "medium",
        "constraints": context.get("constraints", ""),
        "deadline": None,
        "budget": None
    }
    
    try:
        # Call Groq for decomposition
        decomposition = await decompose_project_with_groq(project_data)
        
        # Process tasks and calculate estimates
        tasks = []
        total_cost = 0
        dependencies = {}
        
        for task_data in decomposition.get("tasks", []):
            # Calculate PERT estimates
            opt_days = task_data.get("optimistic_days", 5)
            ml_days = task_data.get("most_likely_days", 10)
            pess_days = task_data.get("pessimistic_days", 15)
            expected_days = calculate_pert_estimate(opt_days, ml_days, pess_days)
            
            # Calculate cost
            task_cost = 0
            for role_data in task_data.get("roles", []):
                role = role_data.get("role", "Developer")
                hours = role_data.get("hours_most_likely", 40)
                rate = DEFAULT_RATES.get(role, 1000)
                task_cost += hours * rate
            
            task = TaskEstimate(
                id=task_data.get("id", str(uuid.uuid4())),
                title=task_data.get("title", "Unnamed Task"),
                description=task_data.get("description", ""),
                category=task_data.get("category", "General"),
                acceptance_criteria=task_data.get("acceptance_criteria", []),
                dependencies=task_data.get("dependencies", []),
                roles=task_data.get("roles", []),
                optimistic_days=opt_days,
                most_likely_days=ml_days,
                pessimistic_days=pess_days,
                expected_days=expected_days,
                risk=task_data.get("risk", "medium"),
                priority=task_data.get("priority", "medium")
            )
            
            tasks.append(task)
            total_cost += task_cost
            dependencies[task.id] = task.dependencies
        
        # Calculate critical path
        task_dicts = [{"id": t.id, "expected_days": t.expected_days} for t in tasks]
        critical_path = calculate_critical_path(task_dicts, dependencies)
        
        # Calculate timeline
        total_duration = sum(t.expected_days for t in tasks if t.id in critical_path) if critical_path else sum(t.expected_days for t in tasks)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=total_duration)
        
        # Create project estimate
        estimate = ProjectEstimate(
            project_id=conversation["project_id"],
            tasks=tasks,
            total_cost=total_cost,
            total_duration_days=total_duration,
            critical_path=critical_path,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            resource_allocation={"rates": DEFAULT_RATES}
        )
        
        # Save to database
        await db.project_estimates.insert_one(estimate.dict())
        
        return estimate
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@api_router.get("/estimates/{project_id}")
async def get_project_estimate(project_id: str):
    """Get project estimate by project ID"""
    estimate = await db.project_estimates.find_one({"project_id": project_id})
    if not estimate:
        raise HTTPException(status_code=404, detail="Project estimate not found")
    
    return estimate

@api_router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    conversation = await db.conversations.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()