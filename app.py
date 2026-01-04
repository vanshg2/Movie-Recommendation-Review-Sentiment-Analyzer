import pickle
import streamlit as st
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import gzip

# -------------------- SESSION STATE --------------------
if "selected_movie_id" not in st.session_state:
    st.session_state.selected_movie_id = None

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

if "selected_actor_id" not in st.session_state:
    st.session_state.selected_actor_id = None

if "base_movie_title" not in st.session_state:
    st.session_state.base_movie_title = None

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0f1115 0%, #0b0d10 100%);
        color: #ffffff;
    }

    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    .block-container {
        padding-top: 1.5rem;
    }

    .poster-card img {
        width: 100%;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.45);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }

    .poster-card img:hover {
        transform: scale(1.04);
        box-shadow: 0 16px 40px rgba(0,0,0,0.65);
    }
    </style>
    """,
    unsafe_allow_html=True
)
#--------------------------Sentiment analyzer -----------------------
sentiment_analyzer = SentimentIntensityAnalyzer()
def analyze_sentiment(text):
    scores = sentiment_analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        return "Positive 😊", compound
    elif compound <= -0.05:
        return "Negative 😠", compound
    else:
        return "Neutral 😐", compound
def summarize_sentiments(reviews):
    counts = {
        "Positive": 0,
        "Neutral": 0,
        "Negative": 0
    }
    scores = []

    for review in reviews:
        content = review.get("content", "")
        label, score = analyze_sentiment(content)
        scores.append(score)

        if "Positive" in label:
            counts["Positive"] += 1
        elif "Negative" in label:
            counts["Negative"] += 1
        else:
            counts["Neutral"] += 1

    avg_score = round(sum(scores) / len(scores), 3) if scores else 0
    return counts, avg_score


# -------------------- CONSTANTS --------------------
API_KEY = "8265bd1679663a7ea12ac168da84d2e8"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500/"
YOUTUBE_API_KEY = "AIzaSyAa2lnBRCPoVbmdjo6ZoPo4YM-PGca1ewE"

# -------------------- API FUNCTIONS --------------------

@st.cache_data(show_spinner=False)
def fetch_movie_cast(movie_id, limit=10):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}&language=en-US"
    try:
        data = requests.get(url, timeout=5).json()
        return data.get("cast", [])[:limit]
    except:
        return []


@st.cache_data(show_spinner=False)
def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        data = requests.get(url, timeout=5).json()
        poster_path = data.get("poster_path")
        if poster_path:
            return POSTER_BASE_URL + poster_path
    except:
        pass
    return "https://via.placeholder.com/500x750?text=No+Poster"


@st.cache_data(show_spinner=False)
def fetch_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        return requests.get(url, timeout=5).json()
    except:
        return {}

@st.cache_data(show_spinner=False)
def fetch_actor_details(actor_id):
    url = f"https://api.themoviedb.org/3/person/{actor_id}?api_key={API_KEY}&language=en-US"
    try:
        return requests.get(url, timeout=5).json()
    except:
        return {}

@st.cache_data(show_spinner=False)
def fetch_actor_credits(actor_id, limit=10):
    url = f"https://api.themoviedb.org/3/person/{actor_id}/combined_credits?api_key={API_KEY}&language=en-US"
    try:
        data = requests.get(url, timeout=5).json()
        credits = data.get("cast", [])
        # Sort by popularity (desc) and keep top N
        credits = sorted(credits, key=lambda x: x.get("popularity", 0), reverse=True)
        return credits[:limit]
    except:
        return []

from googleapiclient.discovery import build


@st.cache_data(show_spinner=False)
def fetch_trailer(movie_title):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        request = youtube.search().list(
            q=f"{movie_title} official trailer",
            part="snippet",
            type="video",
            maxResults=1
        )

        response = request.execute()

        items = response.get("items", [])
        if items:
            return items[0]["id"]["videoId"]

    except Exception as e:
        print(e)

    return None

@st.cache_data(show_spinner=False)
def fetch_movie_reviews(movie_id, limit=None):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={API_KEY}&language=en-US&page=1"
    try:
        data = requests.get(url, timeout=5).json()
        return data.get("results", [])[:limit]
        return results if limit is None else results[:limit]
    except:
        return []


# -------------------- RECOMMENDATION FUNCTION --------------------

def recommend(movie):
    index = movies[movies["title"] == movie].index[0]
    distances = sorted(
        list(enumerate(similarity[index])),
        reverse=True,
        key=lambda x: x[1]
    )

    recs = []
    for i in distances[1:6]:
        recs.append({
            "title": movies.iloc[i[0]].title,
            "movie_id": movies.iloc[i[0]].movie_id
        })
    return recs

# -------------------- STREAMLIT UI --------------------

st.header("🎬 Movie Recommender System")

movies = pickle.load(open("movie_list.pkl", "rb"))
with gzip.open("similarity.pkl.gz", "rb") as f:
    similarity = pickle.load(f)

selected_movie = st.selectbox(
    "Type or select a movie from the dropdown",
    movies["title"].values
)

# -------------------- SHOW RECOMMENDATIONS --------------------

if st.button("Show Recommendation"):
    st.session_state.recommendations = recommend(selected_movie)
    st.session_state.base_movie_title = selected_movie
    st.session_state.selected_movie_id = None

# -------------------- DISPLAY RECOMMENDATIONS --------------------

if st.session_state.recommendations:
    cols = st.columns(5)

    for idx, movie in enumerate(st.session_state.recommendations):
        with cols[idx]:
            poster = fetch_poster(movie["movie_id"])
            st.image(poster)
            st.caption(movie["title"])

            if st.button(
                "View Details",
                key=f"details_{movie['movie_id']}"
            ):
                st.session_state.selected_movie_id = movie["movie_id"]
# -------------------- SIDEBAR : MOVIE INFO --------------------
with st.sidebar:
    st.header("🎬 Movie Info")

    poster = fetch_poster(st.session_state.selected_movie_id)
    details = fetch_movie_details(st.session_state.selected_movie_id)

    st.image(poster, use_container_width=True)

    st.subheader(details.get("title", "N/A"))

    st.write(f"⭐ Rating: {details.get('vote_average', 'N/A')}")
    st.write(f"🕒 Runtime: {details.get('runtime', 'N/A')} mins")
    st.write(f"📅 Release: {details.get('release_date', 'N/A')}")

    genres = ", ".join(g["name"] for g in details.get("genres", []))
    st.write(f"🎭 Genres: {genres if genres else 'N/A'}")


if st.session_state.selected_movie_id is not None:
# -------------------- MOVIE DETAILS + CAST --------------------

    if st.session_state.selected_movie_id:
        details = fetch_movie_details(st.session_state.selected_movie_id)
        poster = fetch_poster(st.session_state.selected_movie_id)
        cast = fetch_movie_cast(st.session_state.selected_movie_id)
    
        st.markdown("---")
        st.header("🎬 Movie Details")
    
        # --- Movie Poster & Basic Info ---
        st.image(poster, width=250)
    
        st.write(f"**Title:** {details.get('title', 'N/A')}")
        st.write(f"**Tagline:** {details.get('tagline', 'N/A')}")
        st.write(f"**Rating:** ⭐ {details.get('vote_average', 'N/A')} ({details.get('vote_count', 0)} votes)")
        st.write(f"**Release Date:** {details.get('release_date', 'N/A')}")
        st.write(f"**Runtime:** {details.get('runtime', 'N/A')} minutes")
        st.write(f"**Status:** {details.get('status', 'N/A')}")
        st.write(f"**Original Language:** {details.get('original_language', 'N/A')}")
    
        genres = ", ".join(g["name"] for g in details.get("genres", []))
        st.write(f"**Genres:** {genres if genres else 'N/A'}")
    
        companies = ", ".join(c["name"] for c in details.get("production_companies", []))
        st.write(f"**Production Companies:** {companies if companies else 'N/A'}")
    
        st.write("**Overview:**")
        st.write(details.get("overview", "No description available"))

    # -------------------- TRAILER SECTION --------------------
    
    st.markdown("## 🎥 Trailer")
    
    video_id = fetch_trailer(details.get("title", ""))
    if video_id:
        st.video(f"https://www.youtube.com/watch?v={video_id}")
    else:
        st.info("Trailer not available.")


    # -------------------- REVIEWS (EXPANDABLE SECTION) --------------------
    
    with st.expander("⭐ User Reviews & Sentiment", expanded=False):
    
        reviews = fetch_movie_reviews(st.session_state.selected_movie_id)
    
        if reviews:
            # ---- SENTIMENT SUMMARY ----
            sentiment_counts, avg_sentiment = summarize_sentiments(reviews)
    
            st.markdown("### 📊 Sentiment Summary")
    
            st.bar_chart(sentiment_counts)
            st.write(f"**Average Sentiment Score:** {avg_sentiment}")
    
            st.markdown("---")
            st.markdown("### 📝 Individual Reviews")
    
            for review in reviews:
                author = review.get("author", "Anonymous")
                content = review.get("content", "")
    
                sentiment_label, score = analyze_sentiment(content)
    
                st.markdown(f"**{author}**")
                st.write(f"Sentiment: {sentiment_label} ({round(score, 2)})")
    
                if len(content) > 700:
                    content = content[:700] + "..."
    
                st.write(content)
                st.markdown("---")
    
        else:
            st.info("No user reviews available for this movie.")

    
    # -------------------- CAST SECTION --------------------
    if cast:
        st.markdown("---")
        st.header("🎭 Cast")

        cast_cols = st.columns(5)

        for idx, actor in enumerate(cast):
            with cast_cols[idx % 5]:
                profile_path = actor.get("profile_path")
                image_url = (
                    POSTER_BASE_URL + profile_path
                    if profile_path
                    else "https://via.placeholder.com/300x450?text=No+Image"
                )

                st.image(image_url, width=140)
                st.caption(actor.get("name", "N/A"))
                st.caption(f"As {actor.get('character', 'N/A')}")

                if st.button(
                    "View Actor",
                    key=f"actor_{actor['id']}"
                ):
                    st.session_state.selected_actor_id = actor["id"]
     # -------------------- ACTOR PROFILE --------------------
if st.session_state.selected_actor_id:
   # st.success(f"Actor clicked! Actor ID = {st.session_state.selected_actor_id}")
   
    actor = fetch_actor_details(st.session_state.selected_actor_id)

    st.markdown("---")
    st.header("👤 Actor Profile")

    # Actor photo
    profile_path = actor.get("profile_path")
    if profile_path:
        actor_image = POSTER_BASE_URL + profile_path
    else:
        actor_image = "https://via.placeholder.com/300x450?text=No+Image"

    st.image(actor_image, width=220)

    # Basic info
    st.write(f"**Name:** {actor.get('name', 'N/A')}")
    st.write(f"**Known For:** {actor.get('known_for_department', 'N/A')}")
    st.write(f"**Gender:** {'Male' if actor.get('gender') == 2 else 'Female' if actor.get('gender') == 1 else 'N/A'}")
    st.write(f"**Birthday:** {actor.get('birthday', 'N/A')}")
    st.write(f"**Place of Birth:** {actor.get('place_of_birth', 'N/A')}")
    st.write(f"**Popularity:** {actor.get('popularity', 'N/A')}")

    # Biography
    st.write("**Biography:**")
    st.write(actor.get("biography", "No biography available."))

# -------------------- ACTOR: KNOWN FOR --------------------

if st.session_state.selected_actor_id:
    credits = fetch_actor_credits(st.session_state.selected_actor_id)

    if credits:
        st.markdown("---")
        st.header("🎞️ Known For")

        cols = st.columns(5)

        for idx, item in enumerate(credits):
            with cols[idx % 5]:
                poster_path = item.get("poster_path")
                poster_url = (
                    POSTER_BASE_URL + poster_path
                    if poster_path
                    else "https://via.placeholder.com/500x750?text=No+Poster"
                )

                title = item.get("title") or item.get("name") or "Untitled"

                st.image(poster_url, width=140)
                st.caption(title)

                if st.button(
                    "View Movie",
                    key=f"knownfor_{item['id']}_{idx}"
                ):
                    # Jump back to movie details
                    st.session_state.selected_movie_id = item["id"]
                    st.session_state.selected_actor_id = None


# -------------------- Footer Watermark --------------------
st.markdown("""
<hr style="border: none; border-top: 1px solid #e5e7eb; margin-top: 40px; margin-bottom: 15px;">
<div style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>
     <b>Build by Vansh Gupta</b>
</div>
""", unsafe_allow_html=True)
