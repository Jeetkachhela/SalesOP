import logging
import json
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """
ROLE:
You are an expert Data Analyst and Operational Intelligence AI. 

TASK:
Your task is to interpret the provided statistical and data quality findings. You must generate a professional, objective, and human-readable operational summary. 

RULES:
- You are ONLY interpreting the provided findings.
- You must explain the findings in clear, concise language for operational users.
- Highlight significant anomalies or missing data risks.

RESTRICTIONS:
- DO NOT invent any metrics, trends, or findings not present in the provided JSON context.
- DO NOT hallucinate statistics.
- If no anomalies are found, simply state that the dataset appears stable.

OUTPUT FORMAT:
Return your response strictly as valid JSON with the following schema:
{
    "summary": "A 2-3 sentence high-level summary of the dataset's operational state.",
    "insights": ["Insight 1", "Insight 2", ...],
    "anomalies_highlighted": ["Anomaly 1", ...],
    "data_quality_warnings": ["Warning 1", ...]
}
"""

def generate_ai_insights(quality_findings: dict, stat_findings: dict) -> dict:
    """
    Safely constructs a context from validated findings and calls Groq for interpretation.
    """
    logger.info("Constructing constrained AI prompt...")
    
    # Context sanitization: Only sending aggregated JSON findings, NO raw data.
    context_payload = {
        "quality_metrics": quality_findings,
        "statistical_metrics": stat_findings["metrics"],
        "anomaly_summaries": stat_findings["anomalies"]
    }
    
    user_prompt = f"Please analyze the following operational findings:\n\n{json.dumps(context_payload, indent=2)}"
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Fast, efficient model for structured JSON
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for deterministic/objective responses
            max_tokens=1024
        )
        
        raw_response = response.choices[0].message.content
        parsed_insights = json.loads(raw_response)
        
        return parsed_insights
        
    except json.JSONDecodeError:
        logger.error("AI response was not valid JSON.")
        return {"error": "AI response validation failed."}
    except Exception as e:
        logger.error(f"AI generation failed: {str(e)}")
        return {"error": "AI interpretation service unavailable."}

def chat_with_insights(question: str, past_chat: list, annotations: list, current_insights: dict) -> str:
    """
    Allows user to ask follow up questions about the dataset, 
    feeding user annotations and past chat history into the LLM context.
    """
    logger.info("Starting conversational follow-up with Groq.")
    
    chat_system_prompt = f"""
ROLE:
You are an expert Data Analyst and Operational Intelligence AI.

CONTEXT:
You are answering a user's follow-up question regarding a dataset.
Here are the current operational insights generated from the deterministic engine:
{json.dumps(current_insights, indent=2)}

USER ANNOTATIONS (CRITICAL CONTEXT):
The user has provided the following annotations on the dataset. You MUST take these into account when answering.
{json.dumps([a for a in annotations], indent=2)}

RULES:
- Answer the user's question directly.
- Use the User Annotations to override your generic assumptions. If the user says a spike is a holiday, agree and incorporate that.
- Keep the tone professional, objective, and operational.
- Do NOT hallucinate data that is not in the context.
"""
    
    messages = [{"role": "system", "content": chat_system_prompt}]
    
    # Add history
    for msg in past_chat[-10:]: # last 10 messages
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": question})
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"AI chat failed: {str(e)}")
        return "I am currently unavailable to answer questions due to a system error."

NL_SYSTEM_PROMPT = """
ROLE:
You are an expert Data Visualizer and Natural Language Data Explorer.
Your goal is to answer the user's question about the dataset and return a matching chart configuration that the frontend can render using Recharts.

CONTEXT PROVIDED:
1. Column Schema and Quality: Information about columns, their types, unique values, and completeness.
2. Statistical metrics: mean, median, standard deviation, min, max per numeric column.
3. Correlation metrics: correlations between numeric columns.
4. Time-series Trends: grouped time-series data points under "series", along with resample period and trend slopes.

RULES:
- Answer the user's question in a clear, concise, and professional tone in the "answer" field.
- Return a "chart_config" object that matches the data.
- The "chart_config" must have:
  - "type": One of: "line", "bar", "scatter", "pie", "none". Choose "none" if the question is purely descriptive and no visualization makes sense.
  - "x_key": The key to plot on the X-axis (e.g., "date" for trends, or a column name).
  - "y_keys": An array of one or more keys to plot on the Y-axis (must match keys in the data points).
  - "data": An array of flat JSON objects containing the values to plot, e.g. [{"date": "2023-01", "payment_value": 150.0}, ...] or [{"name": "Category A", "value": 45}, ...].
- IMPORTANT: Use the time-series trends "series" data when the user asks about time, changes, trends, dates, etc. Ensure the key names you use in "y_keys" and "data" match the actual column names in the dataset.
- DO NOT hallucinate any values. If the information is not present or cannot be computed from the context, state it clearly in the answer and set chart type to "none".

OUTPUT FORMAT:
Return strictly a JSON object with the following schema:
{
    "answer": "Text response explaining the answer to the user's question.",
    "chart_config": {
        "type": "line" | "bar" | "scatter" | "pie" | "none",
        "x_key": "string",
        "y_keys": ["string"],
        "data": [{"key": value, ...}]
    }
}
"""

def nl_query_to_chart(
    question: str, 
    quality_findings: dict, 
    stat_findings: dict, 
    correlation_findings: dict, 
    trend_findings: dict
) -> dict:
    """
    Translates a plain English question into a textual answer and a dynamically-renderable 
    Recharts config, utilizing schema, statistical summaries, correlations, and time series data.
    """
    logger.info("Translating NL query to answer + chart config...")
    
    context_payload = {
        "quality_metrics": {
            "total_rows": quality_findings.get("total_rows"),
            "columns": {col: {"inferred_type": val.get("inferred_type"), "unique_count": val.get("unique_count")} 
                       for col, val in quality_findings.get("columns", {}).items()}
        },
        "statistical_metrics": stat_findings.get("metrics", {}),
        "correlation_metrics": correlation_findings.get("strong_correlations", []),
        "time_series_trends": {
            "primary_datetime_column": trend_findings.get("primary_datetime_column"),
            "resample_period": trend_findings.get("resample_period"),
            # Only send first 50 time-series data points to fit LLM window limits comfortably
            "series": trend_findings.get("series", [])[:50],
            "metrics": {col: {"direction": val.get("direction")} for col, val in trend_findings.get("metrics", {}).items()}
        }
    }
    
    user_prompt = f"Question: {question}\n\nDataset Summary Context:\n{json.dumps(context_payload, indent=2)}"
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": NL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2048
        )
        
        raw_response = response.choices[0].message.content
        parsed = json.loads(raw_response)
        return parsed
        
    except json.JSONDecodeError:
        logger.error("NL query AI response was not valid JSON.")
        return {
            "answer": "I found the answer but encountered an error formatting the chart visualization.",
            "chart_config": {"type": "none", "x_key": "", "y_keys": [], "data": []}
        }
    except Exception as e:
        logger.error(f"NL query AI failed: {str(e)}")
        return {
            "answer": "Sorry, I am currently unable to analyze this question due to an internal system error.",
            "chart_config": {"type": "none", "x_key": "", "y_keys": [], "data": []}
        }
