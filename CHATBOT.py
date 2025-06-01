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

# --- Load KB JSON ---
documents = []

# Load main documentation (lendenclub_clean_data.json)
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

# Load terms and conditions (lendenclub_terms.json)
with open("lendenclub_terms.json", "r", encoding="utf-8") as f:
    terms_data = json.load(f)
    
    # Add company info as a document
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
            # Add section title as a document
            if "title" in section:
                documents.append(Document(
                    page_content=section["title"],
                    metadata={
                        "source": terms_data.get("url", ""),
                        "title": f"Section {section.get('section_number', '')}",
                        "category": "Terms and Conditions"
                    }
                ))
            
            # Add subsections
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

# --- Embed & Store ---
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(documents)

vectorstore = Chroma.from_documents(
    chunks,
    embedding=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),
    persist_directory="./lendeb_chroma"
)
retriever = vectorstore.as_retriever()

# --- Shared LLM ---
llm = ChatGroq(model="llama3-8b-8192")

# --- Tools ---
kb_tool = create_retriever_tool(
    retriever=retriever,
    name="Lendeb_KnowledgeBase_Tool",
    description="Access Lendeb Club documentation"
).as_tool()

web_tool = TavilySearchResults(k=3).as_tool()

# --- Specialized Agent Prompts ---
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

# --- Create Agent Chains ---
def create_agent_chain(domain):
    prompt = PromptTemplate.from_template(AGENT_PROMPTS[domain])
    return LLMChain(llm=llm, prompt=prompt)

main_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(MAIN_AGENT_PROMPT))
agent_chains = {domain: create_agent_chain(domain) for domain in AGENT_PROMPTS.keys()}

# --- Tool Selection Prompt ---
TOOL_SELECTION_PROMPT = """
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
"""

# --- Create Tool Selection Chain ---
tool_selection_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(TOOL_SELECTION_PROMPT))

# --- Tool Selection Function ---
def select_tools(query):
    try:
        # Get tool selection from LLM
        selection = tool_selection_chain.invoke({"query": query})
        selection_text = selection['text'].strip()
        
        # Clean the response text to ensure it's valid JSON
        # Remove any text before the first { and after the last }
        start_idx = selection_text.find('{')
        end_idx = selection_text.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_text = selection_text[start_idx:end_idx]
            try:
                # Parse the JSON
                tool_choice = json.loads(json_text)
                
                # Validate the required fields
                if not isinstance(tool_choice, dict):
                    raise ValueError("Response is not a dictionary")
                
                if "tool" not in tool_choice:
                    raise ValueError("Missing 'tool' field in response")
                
                if tool_choice["tool"] not in ["knowledge_base", "web_search"]:
                    raise ValueError("Invalid tool value")
                
                selected_tool = tool_choice["tool"]
                print(f"Tool selection reason: {tool_choice.get('reason', 'No reason provided')}")
                
                # Execute the selected tool
                if selected_tool == "web_search":
                    try:
                        web_results = web_tool.invoke({"query": query})
                        return "web_search", str(web_results)
                    except Exception as e:
                        print(f"Web search failed: {str(e)}")
                        # Fallback to knowledge base
                        selected_tool = "knowledge_base"
                
                # Try knowledge base (either as primary choice or fallback)
                try:
                    kb_results = kb_tool.invoke({"query": query})
                    if kb_results and len(str(kb_results).strip()) > 0:
                        return "knowledge_base", str(kb_results)
                except Exception as e:
                    print(f"Knowledge base search failed: {str(e)}")
                
                # If both tools fail, return empty results
                return selected_tool, "No results found"
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing tool selection: {str(e)}")
                print(f"Raw response: {json_text}")
                # Default to knowledge base on parsing error
                return "knowledge_base", "Error in tool selection, defaulting to knowledge base"
        else:
            print("No valid JSON found in tool selection response")
            return "knowledge_base", "Invalid tool selection response, defaulting to knowledge base"
            
    except Exception as e:
        print(f"Error in tool selection: {str(e)}")
        # Default to knowledge base on error
        try:
            kb_results = kb_tool.invoke({"query": query})
            return "knowledge_base", str(kb_results)
        except Exception as e:
            print(f"Knowledge base search failed: {str(e)}")
            return "knowledge_base", "No results found"

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

# --- Create Response Combiner Chain ---
combiner_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(COMBINER_PROMPT))

# --- Main Handler ---
def process_query(user_input):
    print("\n🤖 Processing your query...")
    
    # 1. Main agent determines which specialized agents to use
    print("\n🔍 Main Agent analyzing query...")
    try:
        main_response = main_chain.invoke({"query": user_input})
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
    
    # 2. Get context from appropriate tools
    print("\n🔧 Selecting appropriate tools...")
    tool_type, context = select_tools(user_input)
    print(f"Using {tool_type} tool")
    
    # 3. Get responses from each selected agent
    responses = []
    for agent_name in agent_list:
        try:
            print(f"\n📝 Getting response from {agent_name} agent...")
            response = agent_chains[agent_name].invoke({
                "query": user_input,
                "context": context
            })
            responses.append(f"From {agent_name.upper()} Agent:\n{response['text']}")
        except Exception as e:
            print(f"Error getting response from {agent_name} agent: {str(e)}")
            responses.append(f"From {agent_name.upper()} Agent:\nSorry, I encountered an error processing your request.")
    
    # 4. Combine responses if multiple agents were involved
    if len(agent_list) > 1:
        print("\n🔄 Combining responses from multiple agents...")
        try:
            combined_response = combiner_chain.invoke({
                "query": user_input,
                "responses": "\n\n".join(responses)
            })
            final_response = combined_response['text']
        except Exception as e:
            print(f"Error combining responses: {str(e)}")
            final_response = "\n\n".join(responses)
    else:
        final_response = responses[0]
    
    return final_response

# --- CLI Interface ---
if __name__ == "__main__":
    print("🤖 Lendeb Club AI Assistant")
    print("Available domains:")
    for domain in AGENT_PROMPTS.keys():
        print(f"- {domain.upper()}")
    print("\nType 'exit' to quit")
    print("-" * 50)
    
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        try:
            response = process_query(user_input)
            print("\nResponse:")
            print(response)
            print("-" * 50)
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try rephrasing your question.") 