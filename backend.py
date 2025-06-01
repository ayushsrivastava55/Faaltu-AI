from langchain_groq import ChatGroq
from langchain.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools.retriever import create_retriever_tool
import os
import json

# --- API Keys ---
os.environ["GROQ_API_KEY"] = "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"
os.environ["TAVILY_API_KEY"] = "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"
os.environ["GOOGLE_API_KEY"] = "AIzaSyCIYJtE6Fj_sbruYC3nk_FHsQjR7Usn8vU"

# --- Agent Prompts ---
AGENT_PROMPTS = {
    "account": """
    You are an Account Management Specialist for Lendeb Club.
    Focus on: login issues, KYC updates, account deactivation, and account security.
    Use the provided context to answer the user's query.
    
    Query: {query}
    Context: {context}
    
    Provide a clear, step-by-step response:
    """,
    
    "lending": """
    You are a Lending Support Advisor for Lendeb Club.
    Focus on: investment products, withdrawals, portfolio management, and returns.
    Use the provided context to answer the user's query.
    
    Query: {query}
    Context: {context}
    
    Provide a detailed, accurate response:
    """,
    
    "policy": """
    You are a Policy & Compliance Expert for Lendeb Club.
    Focus on: tax rules, fees, recovery processes, and legal compliance.
    Use the provided context to answer the user's query.
    
    Query: {query}
    Context: {context}
    
    Provide a precise, compliant response:
    """,
    
    "support": """
    You are a Support & Escalation Agent for Lendeb Club.
    Focus on: technical issues, promotions, and human support requests.
    Use the provided context to answer the user's query.
    
    Query: {query}
    Context: {context}
    
    Provide a helpful, actionable response:
    """,
    
    "onboarding": """
    You are an Onboarding & General Info Assistant for Lendeb Club.
    Focus on: platform navigation, features, and general information.
    Use the provided context to answer the user's query.
    
    Query: {query}
    Context: {context}
    
    Provide a clear, beginner-friendly response:
    """
}

# --- Main Agent Prompt ---
MAIN_AGENT_PROMPT = """
You are the Main Coordinator for Lendeb Club's AI Assistant.
Analyze the user's query and determine which specialized agents should handle it.
You can route to multiple agents if the query spans multiple domains.

Available agents and their specialties:
1. Account Management (account)
   - Login issues, password reset
   - KYC verification and updates
   - Account deactivation/reactivation
   - Security concerns

2. Lending Support (lending)
   - Investment products and options
   - Withdrawal requests
   - Portfolio management
   - Returns and earnings

3. Policy & Compliance (policy)
   - Tax rules and documentation
   - Service fees and charges
   - Recovery processes
   - Legal compliance

4. Support & Escalation (support)
   - Technical issues
   - App bugs and glitches
   - Promotions and offers
   - Human support requests

5. Onboarding (onboarding)
   - New user registration
   - Platform navigation
   - Basic feature explanation
   - General information

Query: {query}

IMPORTANT: 
- Choose the MOST RELEVANT agent(s) for the specific query
- Only choose 'onboarding' for general questions or new user queries
- Respond with a JSON array of agent names, ordered by relevance
- Example: ["account", "policy"] or ["lending"] or ["support"]
"""

# --- Response Combiner Prompt ---
COMBINER_PROMPT = """
You are a Response Coordinator for Lendeb Club's AI Assistant.
Your task is to combine responses from multiple specialized agents into a single, coherent response.

The user's query was: {query}

Here are the responses from different agents:
{responses}

Please combine these responses into a single, well-structured response that:
1. Addresses all aspects of the user's query
2. Eliminates any redundancy
3. Maintains a consistent tone
4. Presents information in a logical order
5. Clearly indicates which information comes from which domain

Format your response in a clear, organized way.
"""

class ChatbotBackend:
    def __init__(self):
        # Initialize prompts
        self.AGENT_PROMPTS = AGENT_PROMPTS
        self.MAIN_AGENT_PROMPT = MAIN_AGENT_PROMPT
        self.COMBINER_PROMPT = COMBINER_PROMPT
        
        # Initialize components
        self.initialize_components()

    def initialize_components(self):
        # Initialize vector store and tools
        self.documents = self.load_documents()
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.chunks = self.splitter.split_documents(self.documents)
        
        self.vectorstore = Chroma.from_documents(
            self.chunks,
            embedding=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),
            persist_directory="./lendeb_chroma"
        )
        self.retriever = self.vectorstore.as_retriever()
        
        # Initialize LLM
        self.llm = ChatGroq(model="llama3-8b-8192")
        
        # Initialize tools
        self.kb_tool = create_retriever_tool(
            retriever=self.retriever,
            name="Lendeb_KnowledgeBase_Tool",
            description="Access Lendeb Club documentation"
        ).as_tool()
        
        self.web_tool = TavilySearchResults(k=3).as_tool()
        
        # Initialize chains
        self.tool_selection_chain = self.create_tool_selection_chain()
        
        # Initialize specialized agent chains
        self.main_chain = LLMChain(llm=self.llm, prompt=PromptTemplate.from_template(self.MAIN_AGENT_PROMPT))
        self.agent_chains = {domain: LLMChain(llm=self.llm, prompt=PromptTemplate.from_template(prompt)) 
                           for domain, prompt in self.AGENT_PROMPTS.items()}
        self.combiner_chain = LLMChain(llm=self.llm, prompt=PromptTemplate.from_template(self.COMBINER_PROMPT))

    def load_documents(self):
        documents = []
        
        # Load main documentation
        with open("lendenclub_clean_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for url, entry in data.items():
                if isinstance(entry, dict):
                    documents.append(Document(
                        page_content=entry.get("content", ""),
                        metadata={
                            "source": url,
                            "title": entry.get("title", "Untitled"),
                            "category": entry.get("category", ""),
                            "last_modified": entry.get("last_modified", "")
                        }
                    ))

        # Load terms and conditions
        with open("lendenclub_terms.json", "r", encoding="utf-8") as f:
            terms_data = json.load(f)
            
            # Add company info
            if "company_info" in terms_data:
                company_info = terms_data["company_info"]
                company_doc = f"""
                Company Name: {company_info.get('name', '')}
                Trading Name: {company_info.get('trading_name', '')}
                CIN: {company_info.get('cin', '')}
                RBI Registration: {company_info.get('rbi_registration', '')}
                Incorporation: {company_info.get('incorporation', '')}
                """
                documents.append(Document(
                    page_content=company_doc,
                    metadata={
                        "source": terms_data.get("url", ""),
                        "title": "Company Information",
                        "category": "Terms and Conditions"
                    }
                ))
            
            # Add sections and subsections
            if "sections" in terms_data:
                for section in terms_data["sections"]:
                    if "title" in section:
                        documents.append(Document(
                            page_content=section["title"],
                            metadata={
                                "source": terms_data.get("url", ""),
                                "title": f"Section {section.get('section_number', '')}",
                                "category": "Terms and Conditions"
                            }
                        ))
                    
                    if "subsections" in section:
                        for subsection in section["subsections"]:
                            if "content" in subsection:
                                documents.append(Document(
                                    page_content=subsection["content"],
                                    metadata={
                                        "source": terms_data.get("url", ""),
                                        "title": f"Section {section.get('section_number', '')}.{subsection.get('subsection_number', '')}",
                                        "category": "Terms and Conditions"
                                    }
                                ))
        
        return documents

    def create_tool_selection_chain(self):
        prompt = PromptTemplate.from_template("""
        You are a Tool Selection Expert for Lendeb Club's AI Assistant.
        Analyze the user's query and determine whether to use the knowledge base or web search.

        Consider the following:
        1. Knowledge Base is best for:
           - Company-specific information
           - Product details
           - Policies and procedures
           - Terms and conditions
           - Historical information
           - Internal processes

        2. Web Search is best for:
           - Current news and updates
           - Market trends
           - Recent developments
           - Public information
           - External references
           - Real-time data

        Query: {query}

        You must respond with a valid JSON object in this exact format, with no additional text:
        {
            "tool": "knowledge_base",
            "reason": "your reason here"
        }

        The "tool" field must be exactly "knowledge_base" or "web_search".
        The "reason" field should be a brief explanation of your choice.
        """)
        return LLMChain(llm=self.llm, prompt=prompt)

    def process_query(self, query):
        try:
            # 1. Main agent determines which specialized agents to use
            print("\n🔍 Main Agent analyzing query...")
            try:
                main_response = self.main_chain.invoke({"query": query})
                response_text = main_response['text'].strip()
                
                # Clean and parse the response to get agent list
                try:
                    # Find the JSON array in the response
                    start_idx = response_text.find('[')
                    end_idx = response_text.rfind(']') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_text = response_text[start_idx:end_idx]
                        agent_list = json.loads(json_text)
                    else:
                        raise ValueError("No valid JSON array found in response")
                    
                    # Validate agent list
                    valid_agents = ["account", "lending", "policy", "support", "onboarding"]
                    agent_list = [agent for agent in agent_list if agent in valid_agents]
                    
                    if not agent_list:
                        print("Warning: No valid agents selected by main agent. Defaulting to onboarding agent.")
                        agent_list = ["onboarding"]
                        
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing main agent response: {str(e)}")
                    print("Defaulting to onboarding agent.")
                    agent_list = ["onboarding"]
                    
                print(f"Selected agents: {', '.join(agent_list)}")
                
            except Exception as e:
                print(f"Error in main agent selection: {str(e)}")
                print("Defaulting to onboarding agent.")
                agent_list = ["onboarding"]
            
            # 2. Select appropriate tool
            print("\n🔧 Selecting appropriate tools...")
            try:
                tool_selection = self.tool_selection_chain.invoke({"query": query})
                response_text = tool_selection['text'].strip()
                
                # Find the JSON object in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    tool_choice = json.loads(json_text)
                    
                    # Validate tool choice
                    if "tool" not in tool_choice or tool_choice["tool"] not in ["knowledge_base", "web_search"]:
                        raise ValueError("Invalid tool choice in response")
                    
                    selected_tool = tool_choice["tool"]
                    tool_reason = tool_choice.get("reason", "No reason provided")
                else:
                    raise ValueError("No valid JSON object found in response")
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error in tool selection: {str(e)}")
                print("Defaulting to knowledge base.")
                selected_tool = "knowledge_base"
                tool_reason = "Error in tool selection, defaulting to knowledge base"
            
            print(f"Using {selected_tool} tool")
            
            # 3. Get context from selected tool
            if selected_tool == "web_search":
                try:
                    context = str(self.web_tool.invoke({"query": query}))
                except Exception as e:
                    print(f"Web search failed: {str(e)}")
                    context = str(self.kb_tool.invoke({"query": query}))
                    selected_tool = "knowledge_base"
                    tool_reason = "Web search failed, falling back to knowledge base"
            else:
                context = str(self.kb_tool.invoke({"query": query}))
            
            # 4. Get responses from each selected agent
            responses = []
            for agent_name in agent_list:
                try:
                    print(f"\n📝 Getting response from {agent_name} agent...")
                    response = self.agent_chains[agent_name].invoke({
                        "query": query,
                        "context": context
                    })
                    responses.append(f"From {agent_name.upper()} Agent:\n{response['text']}")
                except Exception as e:
                    print(f"Error getting response from {agent_name} agent: {str(e)}")
                    responses.append(f"From {agent_name.upper()} Agent:\nSorry, I encountered an error processing your request.")
            
            # 5. Combine responses if multiple agents were involved
            if len(agent_list) > 1:
                print("\n🔄 Combining responses from multiple agents...")
                try:
                    combined_response = self.combiner_chain.invoke({
                        "query": query,
                        "responses": "\n\n".join(responses)
                    })
                    final_response = combined_response['text']
                except Exception as e:
                    print(f"Error combining responses: {str(e)}")
                    final_response = "\n\n".join(responses)
            else:
                final_response = responses[0]
            
            return {
                "response": final_response,
                "tool_used": selected_tool,
                "tool_reason": tool_reason
            }
            
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error processing your query. Please try again.",
                "tool_used": "error",
                "tool_reason": str(e)
            } 