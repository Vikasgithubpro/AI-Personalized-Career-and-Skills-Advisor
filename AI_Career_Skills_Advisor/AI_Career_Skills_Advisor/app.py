import streamlit as st
import pandas as pd
import spacy
import re
from collections import Counter
import PyPDF2
import docx
import plotly.graph_objects as go

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

st.set_page_config(page_title="AI Personalized Career and Skills Advisor", layout="wide")
st.title("🚀 AI Personalized Career and Skills Advisor")
st.markdown("Analyze your resume, get top career recommendations, dynamic learning plans, and interactive dashboards.")

# Sidebar
st.sidebar.header("Profile Input")
uploaded_resume = st.sidebar.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
manual_skills = st.sidebar.text_area("Or Enter Skills (comma-separated)")
weekly_hours = st.sidebar.slider("Weekly Hours Available for Learning", 2, 40, 8)

# Predefined Roles & Skills
role_skills = {
    "Data Scientist": ["Python", "SQL", "Machine Learning", "Statistics", "Data Visualization"],
    "Full Stack Developer": ["JavaScript", "React", "Node.js", "Databases", "APIs"],
    "Cybersecurity Analyst": ["Networking", "Linux", "Threat Analysis", "SIEM", "Python"],
    "Cloud Engineer": ["AWS", "Docker", "Kubernetes", "Terraform", "Linux"],
    "Product Manager": ["Agile", "Communication", "Market Research", "Roadmapping", "SQL"]
}

common_skills = list(set(sum(role_skills.values(), [])))

# Functions for Resume Parsing
def parse_pdf(file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"PDF parsing error: {e}")
    return text

def parse_docx(file):
    text = ""
    try:
        doc = docx.Document(file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        st.error(f"DOCX parsing error: {e}")
    return text

# Skill Extraction
def extract_skills(text):
    doc = nlp(text)
    skills_found = [token.text for token in doc if token.text.lower() in [s.lower() for s in common_skills]]
    counts = Counter(skills_found)
    max_count = max(counts.values()) if counts else 1
    return {skill: round(count / max_count, 2) for skill, count in counts.items()}

# Education & Experience
def extract_education(text):
    edu_patterns = [r'B\.Tech', r'M\.Tech', r'Bachelor', r'Master', r'PhD']
    education = []
    for pattern in edu_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        education.extend(matches)
    return list(set(education))

def extract_experience(text):
    exp_matches = re.findall(r'(\d+)\s+years?', text, re.IGNORECASE)
    return exp_matches

# Process Resume or Manual Skills
resume_text = ""
user_skills_conf = {}
user_education = []
user_experience = []

if uploaded_resume:
    if uploaded_resume.type == "application/pdf":
        resume_text = parse_pdf(uploaded_resume)
    elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        resume_text = parse_docx(uploaded_resume)
    elif uploaded_resume.type == "text/plain":
        resume_text = uploaded_resume.read().decode("utf-8", errors="ignore")

    if resume_text:
        user_skills_conf = extract_skills(resume_text)
        user_education = extract_education(resume_text)
        user_experience = extract_experience(resume_text)

        st.subheader("📄 Resume Preview & Extracted Info")
        col1, col2 = st.columns([2, 1])
        with col1:
            with st.expander("View Resume Text"):
                st.text_area("Resume Content", resume_text[:10000], height=400)
        with col2:
            st.markdown("**Extracted Skills:**")
            st.write(list(user_skills_conf.keys()))
            st.markdown("**Education:**")
            st.write(user_education)
            st.markdown("**Experience (years mentioned):**")
            st.write(user_experience)

elif manual_skills:
    user_skills_conf = {s.strip(): 1.0 for s in manual_skills.split(",") if s.strip()}

user_skills = list(user_skills_conf.keys())

# Single-Page Combined Interface
st.header("📊 Career Recommendations, Learning Plan & Visualizations")

# Dynamic Career Recommendations
all_roles_scores = []
for role, req_skills in role_skills.items():
    matched = [s for s in req_skills if s in user_skills]
    score = round(len(matched)/len(req_skills)*100, 2) if req_skills else 0
    all_roles_scores.append({"Role": role, "Match %": score, "Matched Skills": matched, "Missing Skills": [s for s in req_skills if s not in matched]})
all_roles_scores = sorted(all_roles_scores, key=lambda x: x['Match %'], reverse=True)
plan = []
for entry in all_roles_scores[:5]:
    for skill in entry['Missing Skills']:
        plan.append({"Week": 1, "Skill": skill, "Resources": [f"Coursera/YouTube Course on {skill}"]})

# Career Recommendations Section
with st.expander("View Career Recommendations"):
    career_df = pd.DataFrame(all_roles_scores[:5])
    st.dataframe(career_df)

# Learning Plan Section
with st.expander("View Personalized Learning Plan"):
    plan_df = pd.DataFrame(plan)
    st.dataframe(plan_df)
    st.download_button(label="📥 Download Learning Plan as JSON",
                       data=plan_df.to_json(orient='records', indent=2),
                       file_name="learning_plan.json",
                       mime="application/json")

# Visualizations Section
with st.expander("View Skills Radar & Heatmap"):
    for entry in all_roles_scores[:5]:
        role = entry['Role']
        req_skills = role_skills.get(role, [])
        all_skills = list(set(user_skills + req_skills))
        user_vals = [user_skills_conf.get(skill, 0) for skill in all_skills]
        target_vals = [1 if skill in req_skills else 0 for skill in all_skills]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=user_vals, theta=all_skills, fill='toself', name='Your Skills'))
        fig.add_trace(go.Scatterpolar(r=target_vals, theta=all_skills, fill='toself', name=f'{role} Required Skills'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=True, title=f"{role} Radar Chart")
        st.plotly_chart(fig, use_container_width=True)

    # Heatmap
    heatmap_data = []
    roles = []
    skills = common_skills
    for role in all_roles_scores[:5]:
        roles.append(role['Role'])
        vals = [1 if skill in role_skills.get(role['Role'], []) else 0 for skill in skills]
        heatmap_data.append(vals)
    heatmap_df = pd.DataFrame(heatmap_data, index=roles, columns=skills)
    fig2 = go.Figure(data=go.Heatmap(z=heatmap_df.values, x=skills, y=roles, colorscale='Viridis'))
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption("Hack2Skill Prototype: AI Career & Skills Advisor")
