import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";
import { Card } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Progress } from "./components/ui/progress";
import { ScrollArea } from "./components/ui/scroll-area";
import { Calendar, Clock, DollarSign, Users, MessageSquare, Download, BarChart3, CheckCircle2, AlertTriangle } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [projectEstimate, setProjectEstimate] = useState(null);
  const [activeTab, setActiveTab] = useState("chat");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const startNewConversation = async () => {
    try {
      const response = await axios.post(`${API}/chat/start`);
      setCurrentConversation(response.data);
      setMessages(response.data.messages);
      setProjectEstimate(null);
      setActiveTab("chat");
    } catch (error) {
      console.error("Failed to start conversation:", error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !currentConversation) return;

    const userMessage = { role: "user", content: inputMessage };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");

    try {
      const response = await axios.post(`${API}/chat/${currentConversation.id}`, {
        content: inputMessage
      });

      const assistantMessage = { role: "assistant", content: response.data.response };
      setMessages(prev => [...prev, assistantMessage]);

      // If ready for analysis, trigger it
      if (response.data.step === "ready_for_analysis") {
        setTimeout(() => analyzeProject(), 1000);
      }
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const analyzeProject = async () => {
    if (!currentConversation) return;

    setIsAnalyzing(true);
    try {
      const response = await axios.post(`${API}/analyze/${currentConversation.id}`);
      setProjectEstimate(response.data);
      setActiveTab("timeline");
      
      const analysisMessage = { 
        role: "assistant", 
        content: `🎉 Analysis complete! I've broken down your project into ${response.data.tasks.length} detailed tasks with a total estimated duration of ${Math.round(response.data.total_duration_days)} days and estimated cost of ₹${response.data.total_cost.toLocaleString()}. Check out the Timeline and Cost tabs for detailed breakdown!` 
      };
      setMessages(prev => [...prev, analysisMessage]);
    } catch (error) {
      console.error("Failed to analyze project:", error);
      const errorMessage = { 
        role: "assistant", 
        content: "I apologize, but there was an error analyzing your project. Please try again or start a new conversation." 
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const exportToCSV = () => {
    if (!projectEstimate) return;

    const csvData = [
      ["Task ID", "Title", "Description", "Expected Days", "Optimistic", "Most Likely", "Pessimistic", "Dependencies", "Risk Level"],
      ...projectEstimate.tasks.map(task => [
        task.id,
        task.title,
        task.description,
        task.expected_days,
        task.optimistic_days,
        task.most_likely_days,
        task.pessimistic_days,
        task.dependencies.join("; "),
        task.risk
      ])
    ];

    const csvContent = csvData.map(row => row.map(cell => `"${cell}"`).join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "project_estimate.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getRiskColor = (risk) => {
    switch (risk.toLowerCase()) {
      case "high": return "bg-red-100 text-red-800";
      case "medium": return "bg-yellow-100 text-yellow-800";
      case "low": return "bg-green-100 text-green-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const calculateTotalCost = () => {
    if (!projectEstimate) return 0;
    return projectEstimate.tasks.reduce((total, task) => {
      return total + task.roles.reduce((roleTotal, role) => {
        return roleTotal + (role.hours_most_likely || 0) * (projectEstimate.resource_allocation?.rates?.[role.role] || 1000);
      }, 0);
    }, 0);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">IT Project Planner</h1>
                <p className="text-sm text-gray-600">AI-Powered Project Estimation & Timeline Planning</p>
              </div>
            </div>
            <Button onClick={startNewConversation} className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
              New Project
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!currentConversation ? (
          <div className="text-center py-20">
            <div className="w-24 h-24 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-8">
              <Calendar className="w-12 h-12 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Welcome to IT Project Planner</h2>
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Get accurate project estimates with AI-powered task decomposition, PERT analysis, and automated timeline generation.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12">
              <Card className="p-6 text-center">
                <MessageSquare className="w-8 h-8 text-blue-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-2">Smart Conversation</h3>
                <p className="text-sm text-gray-600">Multi-turn chat to gather all project requirements</p>
              </Card>
              <Card className="p-6 text-center">
                <Clock className="w-8 h-8 text-green-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-2">PERT Estimation</h3>
                <p className="text-sm text-gray-600">Advanced project estimation with risk analysis</p>
              </Card>
              <Card className="p-6 text-center">
                <Download className="w-8 h-8 text-purple-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-2">Export Ready</h3>
                <p className="text-sm text-gray-600">CSV exports for project management tools</p>
              </Card>
            </div>
            <Button onClick={startNewConversation} size="lg" className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
              Start Project Planning
            </Button>
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="chat" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Conversation
              </TabsTrigger>
              <TabsTrigger value="timeline" disabled={!projectEstimate} className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Timeline & Tasks
              </TabsTrigger>
              <TabsTrigger value="costs" disabled={!projectEstimate} className="flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                Cost Breakdown
              </TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="mt-6">
              <Card className="h-[600px] flex flex-col">
                <ScrollArea className="flex-1 p-4">
                  <div className="space-y-4">
                    {messages.map((message, index) => (
                      <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                          message.role === 'user' 
                            ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white' 
                            : 'bg-gray-100 text-gray-900'
                        }`}>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                      </div>
                    ))}
                    {isAnalyzing && (
                      <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl px-4 py-3">
                          <div className="flex items-center space-x-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                            <p>Analyzing your project...</p>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>
                <div className="border-t p-4">
                  <div className="flex space-x-2">
                    <Input
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      placeholder="Type your message..."
                      onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                      disabled={isAnalyzing}
                    />
                    <Button onClick={sendMessage} disabled={isAnalyzing || !inputMessage.trim()}>
                      Send
                    </Button>
                  </div>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="timeline" className="mt-6">
              {projectEstimate && (
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-2xl font-bold text-gray-900">Project Timeline</h3>
                      <p className="text-gray-600">Detailed task breakdown with PERT estimation</p>
                    </div>
                    <Button onClick={exportToCSV} variant="outline">
                      <Download className="w-4 h-4 mr-2" />
                      Export CSV
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <Card className="p-4">
                      <div className="flex items-center space-x-2">
                        <CheckCircle2 className="w-5 h-5 text-green-600" />
                        <span className="text-sm font-medium">Total Tasks</span>
                      </div>
                      <p className="text-2xl font-bold mt-1">{projectEstimate.tasks.length}</p>
                    </Card>
                    <Card className="p-4">
                      <div className="flex items-center space-x-2">
                        <Clock className="w-5 h-5 text-blue-600" />
                        <span className="text-sm font-medium">Duration</span>
                      </div>
                      <p className="text-2xl font-bold mt-1">{Math.round(projectEstimate.total_duration_days)} days</p>
                    </Card>
                    <Card className="p-4">
                      <div className="flex items-center space-x-2">
                        <DollarSign className="w-5 h-5 text-green-600" />
                        <span className="text-sm font-medium">Estimated Cost</span>
                      </div>
                      <p className="text-2xl font-bold mt-1">{formatCurrency(calculateTotalCost())}</p>
                    </Card>
                    <Card className="p-4">
                      <div className="flex items-center space-x-2">
                        <AlertTriangle className="w-5 h-5 text-orange-600" />
                        <span className="text-sm font-medium">Critical Path</span>
                      </div>
                      <p className="text-2xl font-bold mt-1">{projectEstimate.critical_path.length}</p>
                    </Card>
                  </div>

                  <Card>
                    <div className="p-6">
                      <h4 className="text-lg font-semibold mb-4">Task Breakdown by Category</h4>
                      
                      {/* Category filters */}
                      <div className="flex flex-wrap gap-2 mb-6">
                        {['All', 'Frontend Development', 'Backend Development', 'Database Design', 'Security', 'Deployment', 'Testing', 'Planning'].map(category => (
                          <Button 
                            key={category}
                            variant={selectedCategory === category ? "default" : "outline"}
                            size="sm"
                            onClick={() => setSelectedCategory(category)}
                            className="text-xs"
                          >
                            {category}
                          </Button>
                        ))}
                      </div>

                      <div className="space-y-4">
                        {getFilteredTasks().map((task, index) => (
                          <div key={task.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                            <div className="flex justify-between items-start mb-3">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h5 className="font-semibold text-gray-900">{task.title}</h5>
                                  {task.category && (
                                    <Badge variant="secondary" className="text-xs">
                                      {task.category}
                                    </Badge>
                                  )}
                                  {task.priority && (
                                    <Badge 
                                      className={`text-xs ${
                                        task.priority === 'high' ? 'bg-red-100 text-red-800' :
                                        task.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-green-100 text-green-800'
                                      }`}
                                    >
                                      {task.priority} priority
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 mt-1">{task.description}</p>
                              </div>
                              <Badge className={getRiskColor(task.risk)}>{task.risk} risk</Badge>
                            </div>
                            
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                              <div>
                                <span className="text-xs text-gray-500">Optimistic</span>
                                <p className="font-medium">{task.optimistic_days} days</p>
                              </div>
                              <div>
                                <span className="text-xs text-gray-500">Most Likely</span>
                                <p className="font-medium">{task.most_likely_days} days</p>
                              </div>
                              <div>
                                <span className="text-xs text-gray-500">Pessimistic</span>
                                <p className="font-medium">{task.pessimistic_days} days</p>
                              </div>
                              <div>
                                <span className="text-xs text-gray-500">Expected</span>
                                <p className="font-medium text-blue-600">{Math.round(task.expected_days * 10) / 10} days</p>
                              </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                              {task.dependencies && task.dependencies.length > 0 && (
                                <div>
                                  <span className="text-xs text-gray-500 block mb-1">Dependencies:</span>
                                  <div className="flex flex-wrap gap-1">
                                    {task.dependencies.map(dep => (
                                      <Badge key={dep} variant="outline" className="text-xs">{dep}</Badge>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {task.roles && task.roles.length > 0 && (
                                <div>
                                  <span className="text-xs text-gray-500 block mb-1">Required Roles:</span>
                                  <div className="flex flex-wrap gap-1">
                                    {task.roles.map((role, idx) => (
                                      <Badge key={idx} variant="outline" className="text-xs">
                                        {role.role} ({role.hours_most_likely || 0}h)
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>

                            {task.acceptance_criteria && task.acceptance_criteria.length > 0 && (
                              <div>
                                <span className="text-xs text-gray-500 block mb-1">Acceptance Criteria:</span>
                                <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                                  {task.acceptance_criteria.map((criteria, idx) => (
                                    <li key={idx}>{criteria}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </Card>
                </div>
              )}
            </TabsContent>

            <TabsContent value="costs" className="mt-6">
              {projectEstimate && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">Cost Breakdown</h3>
                    <p className="text-gray-600">Detailed resource allocation and cost analysis</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="p-6">
                      <h4 className="text-lg font-semibold mb-4">Resource Rates (Per Hour)</h4>
                      <div className="space-y-3">
                        {Object.entries(projectEstimate.resource_allocation?.rates || {}).map(([role, rate]) => (
                          <div key={role} className="flex justify-between">
                            <span className="text-gray-700">{role}</span>
                            <span className="font-medium">{formatCurrency(rate)}</span>
                          </div>
                        ))}
                      </div>
                    </Card>

                    <Card className="p-6">
                      <h4 className="text-lg font-semibold mb-4">Cost Summary</h4>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-700">Base Cost</span>
                          <span className="font-medium">{formatCurrency(calculateTotalCost())}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-700">Contingency (15%)</span>
                          <span className="font-medium">{formatCurrency(calculateTotalCost() * 0.15)}</span>
                        </div>
                        <div className="border-t pt-3">
                          <div className="flex justify-between text-lg font-bold">
                            <span>Total Estimated Cost</span>
                            <span className="text-blue-600">{formatCurrency(calculateTotalCost() * 1.15)}</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>

                  <Card className="p-6">
                    <h4 className="text-lg font-semibold mb-4">Task-wise Cost Breakdown</h4>
                    <div className="space-y-4">
                      {projectEstimate.tasks.map((task) => {
                        const taskCost = task.roles.reduce((total, role) => {
                          return total + (role.hours_most_likely || 0) * (projectEstimate.resource_allocation?.rates?.[role.role] || 1000);
                        }, 0);
                        
                        return (
                          <div key={task.id} className="border rounded-lg p-4">
                            <div className="flex justify-between items-center mb-2">
                              <h5 className="font-medium">{task.title}</h5>
                              <span className="font-bold text-blue-600">{formatCurrency(taskCost)}</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                              <div>
                                <span className="text-gray-500">Roles Required:</span>
                                <div className="mt-1">
                                  {task.roles.map((role, idx) => (
                                    <div key={idx} className="flex justify-between">
                                      <span>{role.role}</span>
                                      <span>{role.hours_most_likely || 0}h</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                              <div>
                                <span className="text-gray-500">Duration:</span>
                                <p className="mt-1">{Math.round(task.expected_days * 10) / 10} days</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
};

export default App;