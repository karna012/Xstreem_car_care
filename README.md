# 🚗 Xstreem Car Care - Full-Stack Car Wash Website with AI Chatbot

A fully functional car wash and detailing website for **Xstreem Car Care** featuring:

* 🌐 Customer-facing website
* 🤖 AI chatbot powered by a locally hosted LLM using Ollama
* 🛠️ Admin portal for managing business data
* 🗄️ SQL database for storing and retrieving operational data
* ☁️ Deployment-ready architecture for on-premise or cloud hosting

---

## 📌 Project Overview

Xstreem Car Care is a production-ready web application designed for car wash and detailing businesses.

The platform provides customers with a modern website to explore services, pricing, and contact options, while also offering an AI-powered chatbot that can answer customer questions in real time.

An integrated admin portal allows staff and management to monitor and manage website content, customer interactions, bookings, and business data stored in a SQL database.

The AI chatbot runs locally using Ollama on the same operating system as the web application, enabling fast and private responses without relying entirely on third-party APIs.

---

## ✨ Key Features

### 🌐 Customer Website

* Responsive and mobile-friendly design
* Service listings and pricing information
* Contact forms and booking options
* WhatsApp integration
* QR code support

### 🤖 AI Chatbot

* Powered by Ollama and local LLM models
* Human-like responses
* Handles FAQs and service inquiries
* Responds politely to complaints or harsh questions
* Escalates complex issues to the owner or technical manager
* Uses business-specific knowledge

### 🛠️ Admin Portal

* Secure login authentication
* Dashboard with business metrics
* Manage customer data and inquiries
* View chatbot conversations
* Update services and pricing
* SQL-backed reporting

### 🗄️ SQL Database Integration

* Stores customer records
* Stores bookings and inquiries
* Powers admin dashboard analytics
* Supports CRUD operations

### ☁️ Deployment Ready

* Works on a local machine or server
* Compatible with AWS EC2
* Supports Nginx + Gunicorn
* Domain support through Route 53

---

## 🛠️ Technology Stack

### Backend

* Python
* Flask
* Ollama
* SQLAlchemy / pyodbc

### Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap

### Database

* Microsoft SQL Server / SQLite

### AI Models

* Llama 3.x via Ollama

### Infrastructure

* Git & GitHub
* AWS EC2
* Nginx
* Gunicorn

---

## 🏗️ System Architecture

```text
Customer Browser
      │
      ▼
Frontend Website (HTML/CSS/JS)
      │
      ▼
Flask Backend
 ├── AI Chatbot Module
 │      └── Ollama Local LLM
 ├── Admin Portal
 └── Database Layer
        └── SQL Database
```

---

## 📂 Project Structure

```text
Xstreem_car_care/
├── app.py
├── chatbot.py
├── requirements.txt
├── .gitignore
├── README.md
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── index.html
│   ├── chatbot.html
│   ├── admin.html
│   └── qr_preview.html
├── database/
│   ├── schema.sql
│   └── seed_data.sql
├── uploads/
├── logs/
└── venv/
```

---

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/karna012/Xstreem_car_care.git
cd Xstreem_car_care
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv venv
```

**Windows**

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama

Install Ollama from:
[https://ollama.com](https://ollama.com)

Pull a model:

```bash
ollama pull llama3.2:3b
```

### 5. Configure Environment Variables

Create a `.env` file:

```env
DATABASE_URL=your_database_connection_string
OLLAMA_MODEL=llama3.2:3b
SECRET_KEY=your_secret_key
```

### 6. Run the Application

```bash
python app.py
```

### 7. Access the Application

* Customer Website: `http://127.0.0.1:5000`
* Admin Portal: `http://127.0.0.1:5000/admin`

---

## 🤖 Chatbot Capabilities

The chatbot can answer questions such as:

* What services do you offer?
* How much does ceramic coating cost?
* Do you use branded products?
* Is all your equipment working properly?
* How can I book an appointment?
* What are your working hours?

### Sample Response

> Yes, all our equipment is properly maintained and fully operational. We use premium branded products, and our trained staff ensures your vehicle receives the best care.

---

## 🛠️ Admin Portal Features

* View customer inquiries
* Manage service catalog
* Update pricing
* Monitor chatbot interactions
* Access SQL-powered dashboards
* Manage website content

---

## 🗄️ Database Design

The SQL database stores:

* Customers
* Services
* Bookings
* Chat history
* Admin users
* Website content

---

## 🚀 Deployment

This application can be deployed to:

* AWS EC2
* Render
* Railway
* On-premise Windows/Linux servers

---

## 🔐 Security Best Practices

* Sensitive files excluded via `.gitignore`
* Environment variables stored in `.env`
* Private keys not committed
* Role-based admin access

---

## 📝 .gitignore

```gitignore
venv/
__pycache__/
*.pyc
.env
*.pem
*accessKeys*
credentials.json
token.json
*.db
*.sqlite3
```

---

## 📈 Future Enhancements

* Online payments
* Appointment scheduling calendar
* Multi-language support
* Customer analytics
* CRM integration
* Voice-enabled chatbot

---

## 👨‍💻 Author

**Karan Ramesh**

* GitHub: [https://github.com/karna012](https://github.com/karna012)

---

## 📄 License

This project is licensed under the MIT License.

---

## ⭐ Support

If you found this project useful, please consider starring the repository.
