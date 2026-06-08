from flask import Flask, render_template, request
from transformers import pipeline
import google.generativeai as genai
from config import GEMINI_API_KEY
import textwrap

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# Load Models
question_generator = pipeline("text2text-generation", model="valhalla/t5-base-qg-hl")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# **Home Page**
@app.route("/")
def home():
    return render_template("index.html")

# **Question Generator Page**
@app.route("/question-generator", methods=["GET", "POST"])
def generate_questions():
    if request.method == "GET":
        return render_template("question_generator.html")

    paragraph = request.form.get("paragraph", "").strip()

    if not paragraph:
        return render_template("question_generator.html", error="Please enter a paragraph.")

    chunks = textwrap.wrap(paragraph, width=300)
    all_questions = []

    for chunk in chunks:
        input_text = f"generate questions: {chunk}"
        questions = question_generator(input_text, max_length=50, num_return_sequences=5, num_beams=5)
        all_questions.extend(q["generated_text"] for q in questions)

    return render_template("question_generator_result.html", questions=all_questions)

# **Summarization Page**
@app.route("/summarizer", methods=["GET", "POST"])
def summarize_text():
    if request.method == "GET":
        return render_template("summarizer.html")

    user_text = request.form.get("user_text", "").strip()

    if not user_text:
        return render_template("summarizer.html", error="Please enter text to summarize.")

    # Limit text length
    if len(user_text.split()) > 500:
        user_text = " ".join(user_text.split()[:500])

    summary = summarizer(user_text, max_length=300, min_length=100, do_sample=False)[0]['summary_text']
    return render_template("summarizer_result.html", summary=summary)

# **Question Answering Page**
@app.route("/answer-question", methods=["GET", "POST"])
def answer_question():
    if request.method == "GET":
        return render_template("qa.html")

    context = request.form.get("context", "").strip()
    question = request.form.get("question", "").strip()

    if not context or not question:
        return render_template("qa.html", error="Please provide both context and question.")

    result = qa_pipeline(question=question, context=context)
    answer = result["answer"]

    return render_template("qa_result.html", answer=answer)



# **Study Plan Generator Page**

def generate_study_plan(syllabus, topics, start_date, deadline):
    # UPDATED PROMPT: We explicitly ask for the '***' delimiter
    prompt = f"""
    Create a structured study plan:
    - **Syllabus:** {syllabus}
    - **Topics:** {topics}
    - **Start Date:** {start_date}
    - **Deadline:** {deadline}
    
    FORMATTING RULES:
    1. Break the plan down day-by-day or by specific tasks.
    2. IMPORTANT: Separate each day or major section with the string "***". 
    3. Start the very first line with "***".
    
    Example Format:
    *** Day 1: Introduction
    - Read chapter 1
    *** Day 2: Advanced Topics
    - Practice problems
    """

    try:
        # Note: Standard public models are usually "gemini-1.5-flash". 
        # If "2.5" doesn't work, try changing it to "1.5".
        model = genai.GenerativeModel("models/gemini-2.5-flash") 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        try:
            # Fallback model
            model = genai.GenerativeModel("models/gemini-2.5-pro")
            response = model.generate_content(prompt)
            return response.text
        except Exception as fallback_error:
            return f"*** Error: {str(fallback_error)}. Please check API key."

@app.route("/study-plan", methods=["GET", "POST"])
def study_plan():
    if request.method == "GET":
        return render_template("study_plan.html")

    syllabus = request.form.get("syllabus", "")
    topics = request.form.get("topics", "")
    start_date = request.form.get("start_date", "")
    deadline = request.form.get("deadline", "")

    if not syllabus or not topics or not start_date or not deadline:
        return render_template("study_plan.html", error="Please fill in all fields.")

    # 1. Generate the raw text (which now contains *** separators)
    full_plan_text = generate_study_plan(syllabus, topics, start_date, deadline)

    # 2. SPLIT the text into a list of slides
    #    The prompt ensured that '***' is between every day.
    raw_slides = full_plan_text.split('***')

    # 3. Clean the list (remove empty items created by the split)
    plan_slides = [slide.strip() for slide in raw_slides if slide.strip()]

    # 4. Pass the LIST (plan_slides) to the template, not the string
    return render_template("study_plan_result.html", plan_slides=plan_slides)

# **Run App**
if __name__ == "__main__":
    app.run(debug=True)
