import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Vérifier si la clé API est configurée
if not GOOGLE_API_KEY:
    st.error("La clé API de Google Gemini n'est pas configurée. Veuillez créer un fichier .env avec GOOGLE_API_KEY.")
    st.stop()

# Configuration de l'API Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')


# URL du site web à utiliser pour le RAG
BASE_URL = "https://www.lllfrance.org/"

# Fonction pour extraire le texte d'une page web
@st.cache_data
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text_elements = soup.find_all('p') + soup.find_all('li') + soup.find_all('h1') + soup.find_all('h2') + soup.find_all('h3') + soup.find_all('h4') + soup.find_all('h5') + soup.find_all('h6')
        text = ' '.join([element.get_text() for element in text_elements])
        return text
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la récupération de l'URL {url}: {e}")
        return None

# Fonction pour créer le corpus de documents (ici, un seul document contenant tout le texte du site)
@st.cache_data
def create_corpus(base_url):
    all_text = ""
    visited = set()
    queue = [base_url]
    all_links = set()
    explored_pages = 0
    with st.spinner("Exploration du site web..."):
        while queue and explored_pages <100 :
            current_url = queue.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)
            all_links.add(current_url)
            text = extract_text_from_url(current_url)
            if text:
                all_text += f"Contenu de {current_url}: {text}\n\n"

            try:
                response = requests.get(current_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href and href.startswith(base_url) and href not in visited and href not in queue:
                        queue.append(href)
                    elif href and href.startswith('/') and base_url not in href and base_url + href not in visited and base_url + href not in queue:
                        queue.append(base_url + href)
            except requests.exceptions.RequestException as e:
                st.warning(f"Erreur lors de l'exploration des liens de {current_url}: {e}")
            
            explored_pages+=1
            print(explored_pages)
            
    print(all_links)
    return {"all_content": all_text, "all_links": list(all_links)}

# Fonction pour effectuer la recherche et générer la réponse
def rag_query(query):

    prompt = f"""Répondez à la question suivante en utilisant uniquement les informations fournies 
    dans le site web {BASE_URL} et toutes les sections du site web et toutes les pages disponibles dans le site web. Une recherche internet est aussi possible. 
    
    Indiquez clairement les liens des pages du site que vous avez utilisées pour créer votre réponse à la fin de votre message. La réponse doit contenir les url utilisées.
    
    Si la réponse ne se trouve pas dans le contexte, répondez simplement : "Je ne peux pas répondre à cette question en utilisant les informations fournies."

    Question : {query}

    """

    response = model.generate_content(prompt)
    answer = response.text

    return answer

# Interface Streamlit
st.title("Chatbot d'Information sur l'Allaitement (LLL France)")
st.subheader("Posez vos questions et obtenez des réponses basées sur le contenu de https://www.lllfrance.org/")

# Initialisation de l'état de la session pour le corpus et les messages
#if "corpus" not in st.session_state:
 #   st.session_state["corpus"] = create_corpus(BASE_URL)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Bonjour ! Posez votre question sur l'allaitement basée sur le site de La Leche League France."}]

# Affichage des messages de chat précédents
for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

# Zone de saisie pour la question de l'utilisateur
if prompt := st.chat_input("Votre question :"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.spinner("Génération de la réponse..."):
        ai_response = rag_query(prompt)
        st.session_state["messages"].append({"role": "assistant", "content": ai_response})
        st.chat_message("assistant").write(ai_response)