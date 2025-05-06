from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from crewai import Agent, Task, Crew
from litellm import completion
import time

# CORS configuration
app = FastAPI()

origins = [
    "http://127.0.0.1:5500",  # or your frontend URL if different
    "http://localhost:5500",   # for local development (Live Server)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # Allow frontend URL
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],          # Allow all headers
)

# Pydantic model for the incoming data
class TaxSummaryRequest(BaseModel):
    user_name: str
    age: int
    profession: str
    bank_statement: str

# Dummy class for LLM completion (you will replace this with your actual logic)
class GeminiLLM:
    def __init__(self, model_name="gemini/gemini-2.0-flash-lite", temperature=0.2):
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = "AIzaSyCPj0blvKdy_cW8AxbDDqu5N9IHd5REpYc"  # Replace with your actual key

    def run(self, messages):
        response = completion(
            model=self.model_name,
            messages=messages,
            api_key=self.api_key,
            litellm_provider="google",
            temperature=self.temperature
        )
        return response["choices"][0]["message"]["content"]

    def __call__(self, prompt, stop=None):
        messages = [{"role": "user", "content": prompt}]
        return self.run(messages)

llm = GeminiLLM()

@app.post("/generate-tax-summary")
async def generate_tax_summary(request: TaxSummaryRequest):
    user_name = request.user_name
    age = request.age
    profession = request.profession
    bank_statement = request.bank_statement

    # Defining Agents and Tasks (same as your original code)
    doc_parsing_agent = Agent(
        role='Document Parsing Expert',
        goal='Extract structured income and expense data from bank statements',
        backstory='Expert in parsing financial documents using OCR and semantic analysis.',
        llm=llm
    )

    income_classifier = Agent(
        role='Income Classification Expert',
        goal='Classify income into Salary, Business, Capital Gains, Other Sources',
        backstory='Specialist in Indian income tax categories and transaction classification.',
        llm=llm
    )

    deduction_agent = Agent(
        role='Deduction Analysis Advisor',
        goal='Identify all applicable deductions under Indian tax law (80C, 80D, etc.)',
        backstory='Expert in Indian tax-saving instruments and deduction mapping.',
        llm=llm
    )

    tax_calc_agent = Agent(
        role='Tax Computation Bot',
        goal='Calculate tax liability under both new and old regimes as per Indian slabs',
        backstory='Built to precisely compute tax with surcharges and cess included.',
        llm=llm
    )

    optimization_agent = Agent(
        role='Tax Optimization Consultant',
        goal='Compare both regimes, recommend best one, and generate final tax summary for user',
        backstory='Expert in minimizing tax liability and creating readable tax summaries.',
        llm=llm
    )

    # Defining Tasks
    parse_task = Task(
        description=f"""
        Parse the bank statement for user {user_name}, age {age}, profession: {profession}.
        Extract structured data like salary, investments, business/freelance income, deductions, etc.
        Bank Statement:
        {bank_statement}
        """,
        expected_output="JSON with categorized income, expenses, and investments",
        agent=doc_parsing_agent
    )

    classify_task = Task(
        description="Classify parsed income into tax heads (Salary, Business, Capital Gains, Other Sources)",
        expected_output="Structured income under tax heads",
        agent=income_classifier
    )

    deduction_task = Task(
        description="Identify deductions applicable under Indian IT Act like 80C, 80D, etc.",
        expected_output="List of deductions and amounts",
        agent=deduction_agent
    )

    tax_task = Task(
        description="""Compute tax liability under both Old and New Regimes based on current Indian income tax slabs.""",
        expected_output="Detailed slab-wise tax calculation for Old and New Regimes",
        agent=tax_calc_agent
    )

    optimize_task = Task(
        description=f"""
        Analyze both tax regimes and deductions for {user_name}.
        Recommend the optimal tax regime and generate a final user-friendly summary.
        """,
        expected_output="Formatted text summary in markdown format",
        agent=optimization_agent
    )

    # Create Crew
    crew = Crew(
        agents=[doc_parsing_agent, income_classifier, deduction_agent, tax_calc_agent, optimization_agent],
        tasks=[parse_task, classify_task, deduction_task, tax_task, optimize_task],
        verbose=True
    )

    # Actually run the Crew now
    result = crew.kickoff()

    # Clean if wrapped inside ```
    final_output = str(result)

    if final_output.strip().startswith("```") and final_output.strip().endswith("```"):
        final_output = final_output.strip().lstrip("```").rstrip("```").strip()

    return JSONResponse(content={"tax_summary": final_output})

