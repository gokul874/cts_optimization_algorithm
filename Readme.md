## 🏥 Provider Network Optimization – Team NETSENSE

*Team No:* 1  
*College:* RMKCET  
*Hackathon:* Healthcare Hack 2025  

---

## 📌 Problem Statement
Healthcare networks must balance *adequate member access, **provider quality, and **cost control*.  
Our objective is to build a *network optimization tool* that ensures:

- ✅ 95%+ access compliance (CMS standards)  
- ✅ Reduced network costs by *8–12%*  
- ✅ Maintains provider quality & availability  

---

## 🚀 Solution Overview

### 🔹 Member Side
1. *Location Capture* → GPS / Map-based longitude & latitude.  
2. *Provider Selection* → Hospital | Nursing Home | Scan Centre | Pharmacy.  
3. *Smart Search & Ranking* → Finds providers within *15 km*, prioritizing:  
   - CMS Rating → Distance → Cost → Availability.  
4. *Navigation* → Click provider → Opens in Google Maps for directions.  

### 🔹 Admin Side
1. *Dataset Upload* → Admin uploads Member & Provider CSV. Data cleaned & processed.  
2. *Optimization Rules* → Member-centered matching (BallTree, 15 km radius).  
3. *Access & Cost Analysis* →  
   - Compute % of members served.  
   - Compare *Original vs Optimized Cost* (Profit/Loss %).  
4. *Unused Provider Detection* → Download CSV of unused providers.  
5. *Visualization & Reporting* →  
   - Text reports (Access %, Cost Savings, Feasibility).  
   - Map view (🟢 served vs 🔴 unserved members).  
   - Category-wise optimization (Hospital, Nursing, Scan, Supplier).  

---

## ⚙ Technical Stack

### Member Side
- *Frontend*: HTML, CSS, JavaScript, Bootstrap  
- *Maps & Location*: Leaflet.js, Google Maps API, Browser GPS  
- *Backend*: Flask (Python), Pandas (CSV handling), Scikit-learn (BallTree)  

### Admin Side
- *Frontend*: HTML, CSS, JavaScript, Bootstrap  
- *Visualization*: Chart.js / Plotly.js, Leaflet Maps  
- *Backend*: Flask (Python), Pandas, NumPy, Scikit-learn (BallTree)  
- *Reporting*: Matplotlib, Seaborn, Flask Templates  
- *Storage*: CSV uploads (members & providers), downloadable optimization reports  

---

## 🏗 Architecture
- *Input*: Member & Provider datasets (CSV)  
- *Process*: Data cleaning → Optimization Algorithm (Rating → Cost → Distance → Availability)  
- *Output*:  
  - Optimized provider assignments  
  - Access % & Cost Analysis  
  - Reports & Visualizations  

---

## 📊 Features
- Smart provider search & ranking  
- Cost optimization (8–12% savings)  
- 95%+ access compliance  
- CSV upload/download for admins  
- Visualization (maps, charts, text reports)  
- Google Maps integration for navigation  

---

## ▶ How to Run
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py
*
