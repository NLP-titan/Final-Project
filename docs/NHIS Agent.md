  
User Message  
     ↓  
Agent (ReAct reasoning)  
     ↓  
Decides which tool to call  
     ↙          ↓          ↘  
Policy       Medicines    Facility  
Retriever    Checker      Checker  
(Vector DB)  (Structured) (Structured)

**Building the App**

1. **Knowledgbe base construction**

Sources to collect:

* NHIS benefit package document (what is and isn't covered)  
* NHIS medicines list (the official drug formulary)  
* List of accredited facilities by region  
* NHIS membership, registration and renewal guidelines  
* Common denial/dispute resolution procedures

Check NHIS website or onine for data and tag each chunk by category (coverage, medicines, facilities, enrollment, disputes) 

| Data Type | Example | Best Storage |
| ----- | ----- | ----- |
| Narrative policy text | Benefit package document, membership guidelines | Vector DB (semantic search) |
| Structured lists | Accredited facilities, medicines formulary | Structured DB or CSV (exact/fuzzy lookup) |

2. **RAG pipeline setup**

For policy documents;

* Chunk documents intelligently (by section, not arbitrary character splits)  
* Embed chunks using a sentence embedding model eg sentence-transformers  
* Store in a vector database  eg ChromaDB, FAISS, Pinecone  
* Build a retriever that takes a user query and returns the most relevant policy chunks

For  structured list, store data in a csv or a structured DB (SQL)

3. **Building the Agent**

Tool Integration

* Policy Retriever    
* Medicines Checker  
* Facility Checker

Build Dialogue Management

4. **Demo Interface**  
5. **Evaluation**

Evaluate on 30 test cases covering different scenarios (coverage, drug entitlement, facility accreditation, membership/renewal, rights dispute)

6. **Report**

I. Problem identification  
ii. Literature Review  
iii. Solution and Evaluation  
iv. Ethical analysis  
v. Each team member’s contribution to the project

**Appendix**

Coverage queries (*"Is dialysis covered under NHIS?"*)  
Drug entitlement (*"Should I pay for this medication?"*)  
Facility accreditation (*"Is this hospital NHIS-accredited?"*)  
Membership/renewal (*"My card expired, what do I do?"*)  
Rights disputes (*"They turned me away, is that allowed?"*)  
