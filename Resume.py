import sys
sys.path.append(r"C:\Users\Admin\anaconda3\Scripts")

import streamlit as st
import spacy
import mysql.connector
from transformers import pipeline
import re
import fitz
import pandas as pd
import io

# Database Initialization
def initialize_database():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="soundarya2005"
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS resume_db")
    cursor.execute("USE resume_db")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        contact VARCHAR(20),
        email VARCHAR(255),
        skills TEXT,
        education TEXT,
        experience TEXT,
        summary TEXT
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

initialize_database()

nlp = spacy.load("en_core_web_sm")
summarizer = pipeline("summarization")

st.title("Resume Parser")

uploaded_files = st.file_uploader("Upload your resumes (PDF format, multiple allowed)", type="pdf", accept_multiple_files=True)

# Function to extract name from PDF
def extract_name(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_with_fonts = []
    
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_with_fonts.append({
                            "text": span["text"],
                            "font_size": span["size"]
                        })

    text_with_fonts.sort(key=lambda x: -x['font_size'])

    for item in text_with_fonts:
        text = item['text'].strip()
        if re.match(r"^[A-Za-z\s]+$", text) and len(text.split()) <= 3:
            return text
    return "Unknown"

# Extract text from PDF
def extract_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Extract contact info
def extract_contact_info(text):
    phone = re.search(r"(\+91\s?)?\b\d{10}\b", text)
    email = re.search(r"\S+@\S+\.\S+", text)
    return phone.group(0) if phone else None, email.group(0) if email else None

# Extract skills
def extract_skills(text):
    ml_keywords = [
        'python', 'sql', 'nlp', 'computer vision', 'tensorflow', 'keras', 
        'pytorch', 'scikit-learn', 'data analysis', 'data visualization',
        'mlops', 'docker', 'kubeflow', 'cloud computing', 'aws', 'azure',
        'gcp', 'hyperparameter tuning', 'feature engineering', 'model deployment',
        'big data', 'spark', 'data wrangling', 'pipeline automation'
    ]
    
    text_lower = text.lower()
    detected_skills = [skill for skill in ml_keywords if skill in text_lower]
    return ", ".join(set(detected_skills)) if detected_skills else "No specific skills detected"

# Extract education
def extract_education(text):
    education_section = re.search(r"EDUCATION\s*([\s\S]+?)(?=\n[A-Z]+\s|\n\n|$)", text, re.IGNORECASE)
    if education_section:
        education_text = education_section.group(1).strip()
    else:
        education_text = "No education details found"

    education_keywords = ["B.E", "Bachelor", "M.Tech", "MBA", "HSC", "SSLC", "Engineering", "CGPA", "Score"]
    education_lines = [line.strip() for line in education_text.split("\n") if any(keyword in line for keyword in education_keywords)]
    
    return " | ".join(education_lines) if education_lines else education_text

# Extract experience
def extract_experience(text):
    experience_section = re.search(r"WORK EXPERIENCE\s*([\s\S]+?)(?=\n[A-Z]+\s|\n\n|$)", text, re.IGNORECASE)
    if experience_section:
        experience_text = experience_section.group(1).strip()
    else:
        experience_text = "No detailed experience found"

    return experience_text

# Summarize text
def summarize_text(text):
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)[0]["summary_text"]
    return summary

# Store data to database
def store_to_db(data):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="soundarya2005",
        database="resume_db"
    )
    cursor = conn.cursor()
    
    query = """
        INSERT INTO resume_data (name, contact, email, skills, education, experience, summary)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        data["name"], data["contact"], data["email"], data["skills"],
        data["education"], data["experience"], data["summary"]
    ))
    
    conn.commit()
    cursor.close()
    conn.close()

# Process uploaded files
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        name = extract_name(file_bytes)
        resume_text = extract_text_from_pdf(file_bytes)
        contact, email = extract_contact_info(resume_text)
        skills = extract_skills(resume_text)
        education = extract_education(resume_text)
        experience = extract_experience(resume_text)
        summary = summarize_text(resume_text)
        
        resume_data = {
            "name": name,
            "contact": contact,
            "email": email,
            "skills": skills,
            "education": education,
            "experience": experience,
            "summary": summary
        }
        
        store_to_db(resume_data)
        
        st.write(f"**Name:** {name}")
        st.write(f"**Contact:** {contact}")
        st.write(f"**Email:** {email}")
        st.write(f"**Skills:** {skills}")
        st.write(f"**Education:** {education}")
        st.write(f"**Experience:** {experience}")
        st.write(f"**Summary:** {summary}")
        st.write("---")

# Function to download data as Excel
def download_data():
    conn = mysql.connector.connect(host="localhost", user="root", password="soundarya2005", database="resume_db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resume_data")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    df = pd.DataFrame(rows, columns=["ID", "Name", "Contact", "Email", "Skills", "Education", "Experience", "Summary"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Resume Data")
    output.seek(0)
    return output

st.download_button("Download", download_data(), "resume_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
