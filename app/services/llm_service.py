import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import asyncio
from openai import AsyncOpenAI
from ..config import settings
from ..models import ChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.openai_model



    async def _parse_and_execute_tool_call(self, response_text: str) -> str:
        """Parse JSON function call from response text and execute via MCP"""
        logger.debug(f"Parsing tool call from response: {response_text}")
        logger.info(f"Attempting to parse and execute MCP tool call")
        try:
            import json
            import re
            
            function_call = None
            
            try:
                function_call = json.loads(response_text.strip())
                if isinstance(function_call, dict) and "function" in function_call:
                    pass
                else:
                    raise json.JSONDecodeError("Not a function call", response_text, 0)
            except json.JSONDecodeError:
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                matches = re.findall(json_pattern, response_text)
                function_call = None
                for match in matches:
                    try:
                        parsed = json.loads(match)
                        if isinstance(parsed, dict) and "function" in parsed:
                            function_call = parsed
                            break
                    except json.JSONDecodeError:
                        continue
                
                if not function_call:
                    return "Error: Could not find JSON function call in response"
            
            function_name = function_call.get("function")
            parameters = function_call.get("parameters", {})
            logger.debug(f"Function name: {function_name}, Parameters: {parameters}")
            
            try:
                from ..mcp_server import mcp
                
                tool = await mcp.get_tool(function_name)
                if tool and hasattr(tool, 'fn') and callable(tool.fn):
                    result = await tool.fn(**parameters)
                    
                    if isinstance(result, list) and result:
                        formatted_result = []
                        for i, doc in enumerate(result):
                            if isinstance(doc, dict):
                                formatted_doc = {
                                    "document_number": i + 1,
                                    "title": doc.get("metadata", {}).get("title", "Untitled Document"),
                                    "url": doc.get("metadata", {}).get("url", doc.get("metadata", {}).get("source_url", "No URL available")),
                                    "content": doc.get("content", "No content available")[:1000] + ("..." if len(doc.get("content", "")) > 1000 else ""),
                                    "metadata": doc.get("metadata", {}),
                                    "relevance_score": doc.get("_search_score", "N/A")
                                }
                                formatted_result.append(formatted_doc)
                        return json.dumps(formatted_result, indent=2)
                    else:
                        return json.dumps(result, indent=2)
                else:
                    return f"Error: MCP tool '{function_name}' not found or not callable"
                    
            except Exception as e:
                logger.error(f"Error calling MCP tool '{function_name}': {str(e)}")
                return f"Error calling MCP tool '{function_name}': {str(e)}"
                
        except Exception as e:
            logger.error(f"Error parsing/executing MCP tool call: {str(e)}")
            return f"Error executing MCP tool call: {str(e)}"


    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Generate chat completion with custom tool calling support for VLLM"""
        try:
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            system_message = {
                "role": "system",
                "content": """You are ChatGTG, an AI assistant with access to a document knowledge base.

IMPORTANT: When users ask about documents, information, or data, respond with ONLY a JSON function call in this exact format:

For searching documents (enhanced relevance):
{"function": "search_documents", "parameters": {"query": "search terms", "limit": 10}}

For advanced semantic search (best for complex queries):
{"function": "search_documents_semantic", "parameters": {"query": "search terms", "limit": 10}}

For getting all documents:
{"function": "get_all_documents", "parameters": {"limit": 20}}

For document count:
{"function": "get_document_count", "parameters": {}}

For metadata search:
{"function": "search_documents_by_metadata", "parameters": {"metadata_filter": {"key": "value"}, "limit": 10}}

SEARCH STRATEGY:
- Use "search_documents_semantic" for complex queries requiring deep understanding and conceptual questions (e.g., "what is X?")
- Use "search_documents" for general keyword-based searches and specific technical queries
- Both provide relevance-ranked results with context-aware scoring

RULES:
- Output ONLY the JSON, no explanations
- No text before or after the JSON
- No code blocks or formatting
- No apologies or disclaimers

For non-document questions, respond normally."""
            }
            messages.insert(0, system_message)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            assistant_response = response.choices[0].message.content
            logger.info(f"First LLM response: {assistant_response}")
            logger.info(f"Function detection check: function in response = {'"function"' in assistant_response if assistant_response else False}, has braces = {'{' in assistant_response if assistant_response else False}")
            
            if assistant_response and '"function"' in assistant_response and '{' in assistant_response:
                logger.info(f"Function call detected, executing MCP tool...")
                tool_result = await self._parse_and_execute_tool_call(assistant_response)
                logger.info(f"MCP tool executed, result length: {len(str(tool_result))}")
                
                original_user_message = messages[1]  # Skip the system message
                
                conversational_messages = [
                    {
                        "role": "system",
                        "content": """You are ChatGTG, a helpful AI assistant. Your job is to analyze document search results and provide comprehensive, detailed responses to users' questions.

IMPORTANT RESPONSE GUIDELINES:
- Provide detailed, comprehensive answers (aim for 3-5 paragraphs minimum)
- Always include source document references with URLs when available
- Structure your response with clear sections and bullet points when appropriate
- Quote relevant excerpts from the documents to support your answer
- If multiple documents are found, synthesize information from all relevant sources
- Include document titles and URLs in your response like: "According to [Document Title](URL)..."
- Never return JSON or code blocks in your final response
- Be thorough and informative - users want detailed explanations
- If no relevant documents are found, explain what you searched for and suggest alternative queries

RESPONSE FORMAT:
1. Start with a clear, direct answer to the user's question
2. Provide detailed explanation with supporting information from documents
3. Include relevant quotes or excerpts from source documents
4. List source documents with titles and URLs at the end
5. Suggest related topics or follow-up questions if appropriate"""
                    },
                    original_user_message,
                    {
                        "role": "user",
                        "content": f"I searched for documents related to your question and found the following results:\n\n{tool_result}\n\nBased on these documents, please provide a comprehensive, detailed answer to my original question. Include document URLs and titles in your response, quote relevant sections, and structure your answer with clear sections. Make your response thorough and informative (3-5 paragraphs minimum)."
                    }
                ]
                
                logger.info(f"Making second LLM call to process tool results...")
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=conversational_messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                )
                logger.info(f"Second LLM call completed, returning final response")
                logger.info(f"Final response content: {final_response.choices[0].message.content}")
                
                return ChatResponse(
                    id=final_response.id,
                    object=final_response.object,
                    created=final_response.created,
                    model=final_response.model,
                    choices=[
                        {
                            "index": choice.index,
                            "message": {
                                "role": choice.message.role,
                                "content": choice.message.content
                            },
                            "finish_reason": choice.finish_reason
                        }
                        for choice in final_response.choices
                    ],
                    usage={
                        "prompt_tokens": final_response.usage.prompt_tokens,
                        "completion_tokens": final_response.usage.completion_tokens,
                        "total_tokens": final_response.usage.total_tokens
                    }
                )
            
            else:
                logger.info(f"No function call detected, returning original response")
                return ChatResponse(
                    id=response.id,
                    object=response.object,
                    created=response.created,
                    model=response.model,
                    choices=[
                        {
                            "index": choice.index,
                            "message": {
                                "role": choice.message.role,
                                "content": choice.message.content
                            },
                            "finish_reason": choice.finish_reason
                        }
                        for choice in response.choices
                    ],
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise

llm_service = LLMService()
