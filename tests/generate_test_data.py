"""
Generate test data for evaluating the RAG and recommendation systems.
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Define paths
OUTPUT_DIR = "tests/data"
TEST_QUERIES_PATH = f"{OUTPUT_DIR}/test_queries.json"
USER_PROFILES_PATH = f"{OUTPUT_DIR}/user_profiles.json"
BENCHMARK_QUERIES_PATH = f"{OUTPUT_DIR}/benchmark_queries.json"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_test_queries():
    """Generate diverse test queries with expected sources using substrings for flexible matching."""
    queries = [
        # Payments and financial queries
        {
            "query": "How do payments work?",
            "expected_sources": ["payments", "shakers-qa-dataset"],
            "expected_topics": ["payments", "escrow", "fees"],
            "should_be_out_of_scope": False,
        },
        {
            "query": "What payment methods does Shakers accept?",
            "expected_sources": ["payments", "shakers-qa-dataset"],
            "expected_topics": [
                "payment methods",
                "credit card",
                "paypal",
                "bank transfer",
            ],
            "should_be_out_of_scope": False,
        },
        {
            "query": "How does Shakers handle escrow payments?",
            "expected_sources": ["payments"],
            "expected_topics": ["escrow", "milestone", "protection"],
            "should_be_out_of_scope": False,
        },
        # {
        #     "query": "What fees does Shakers charge?",
        #     "expected_sources": ["payments", "shakers-qa-dataset"],
        #     "expected_topics": ["fees", "service fee", "client fee", "freelancer fee"],
        #     "should_be_out_of_scope": False
        # },
        # Freelancer queries
        {
            "query": "What is a freelancer on Shakers?",
            "expected_sources": ["freelancers"],
            "expected_topics": ["freelancer", "contractor", "professional"],
            "should_be_out_of_scope": False,
        },
        {
            "query": "How do I become a freelancer on Shakers?",
            "expected_sources": ["freelancers", "getting-started-guide"],
            "expected_topics": ["freelancer", "registration", "profile"],
            "should_be_out_of_scope": False,
        },
        # {
        #     "query": "What types of freelancers can I find on Shakers?",
        #     "expected_sources": ["freelancers", "freelancer-profiles"],
        #     "expected_topics": ["types", "categories", "development", "design", "writing"],
        #     "should_be_out_of_scope": False
        # },
        # Talent search queries
        {
            "query": "How can I find the right talent on Shakers?",
            "expected_sources": ["finding_talent"],
            "expected_topics": ["search", "filters", "matching", "skills"],
            "should_be_out_of_scope": False,
        },
        {
            "query": "How do I search for freelancers with specific skills?",
            "expected_sources": ["finding_talent"],
            "expected_topics": ["search", "filters", "skills", "expertise"],
            "should_be_out_of_scope": False,
        },
        {
            "query": "I need an Android developer with experience",
            "expected_sources": ["freelancer-profiles"],
            "expected_topics": ["android", "developer", "mobile", "profiles"],
            "should_be_out_of_scope": False,
        },
        # {
        #     "query": "Looking for React developers",
        #     "expected_sources": ["freelancer-profiles"],
        #     "expected_topics": ["react", "developer", "web", "frontend"],
        #     "should_be_out_of_scope": False
        # },
        {
            "query": "Find me UI/UX designers",
            "expected_sources": ["freelancer-profiles"],
            "expected_topics": ["ui", "ux", "design", "designer"],
            "should_be_out_of_scope": False,
        },
        {
            "query": "Need a content writer for my blog",
            "expected_sources": ["freelancer-profiles"],
            "expected_topics": ["content", "writer", "writing", "blog"],
            "should_be_out_of_scope": False,
        },
        # Platform queries
        {
            "query": "How does Shakers verify freelancers?",
            "expected_sources": ["freelancers"],
            "expected_topics": ["verification", "quality control", "vetting"],
            "should_be_out_of_scope": False,
        },
        {
            "query": "What is the technical architecture of Shakers?",
            "expected_sources": ["shakers-technical-documentation"],
            "expected_topics": ["architecture", "technical", "platform"],
            "should_be_out_of_scope": False,
        },
        # Out of scope queries
        {
            "query": "How do I cook pasta?",
            "expected_sources": [],
            "expected_topics": [],
            "should_be_out_of_scope": True,
        },
        {
            "query": "What's the weather like today?",
            "expected_sources": [],
            "expected_topics": [],
            "should_be_out_of_scope": True,
        },
        {
            "query": "Tell me about the history of ancient Rome",
            "expected_sources": [],
            "expected_topics": [],
            "should_be_out_of_scope": True,
        },
        {
            "query": "How do I train my dog?",
            "expected_sources": [],
            "expected_topics": [],
            "should_be_out_of_scope": True,
        },
    ]

    with open(TEST_QUERIES_PATH, "w") as f:
        json.dump(queries, f, indent=2)

    print(f"Generated {len(queries)} test queries in {TEST_QUERIES_PATH}")
    return queries


def generate_benchmark_queries():
    """Generate benchmark queries with expected answers and sources using substrings for flexible matching."""
    benchmarks = [
        {
            "query": "How do payments work?",
            "expected_sources": ["payments", "shakers-qa-dataset"],
            "expected_answer": "Shakers uses a secure escrow system for payments between clients and freelancers. When a client creates a project, they set a budget or hourly rate. Once a freelancer is hired, the client funds the project by placing the agreed amount in escrow. For fixed-price projects, clients can create milestones and release payments as deliverables are completed. For hourly projects, freelancers log their hours using the time-tracking system, and clients are billed weekly. Once the client approves the work, the funds are released to the freelancer's Shakers account. Freelancers can withdraw their earnings through various methods, including bank transfers, PayPal, and other payment services. Shakers charges a 5% fee to clients and a 10% fee to freelancers.",
        },
        {
            "query": "What is a freelancer on Shakers?",
            "expected_sources": ["freelancers"],
            "expected_answer": "A freelancer on Shakers is an independent professional who offers their services to clients on a project-by-project basis. Freelancers are not employees of either Shakers or the clients they work with but instead operate as independent contractors. Shakers hosts a diverse range of professionals across multiple disciplines including Development & IT, Design & Creative, Writing & Content, Marketing & Sales, and Business & Consulting. Each freelancer has a comprehensive profile showing their professional headline, skills, portfolio, education, certifications, client reviews, rates, and availability status.",
        },
        {
            "query": "I need an Android developer, can you help me find one?",
            "expected_sources": ["freelancer-profiles"],
            "expected_answer": "Yes, there's an Android specialist named Miguel Rodriguez available on Shakers. He's a Mobile Developer with 8 years of experience building native applications with Kotlin and Java. He specializes in creating high-performance apps with elegant UIs and seamless backend integration. His skills include Kotlin, Java, Android SDK, Jetpack Compose, RESTful APIs, GraphQL, Firebase, and Room Database. Miguel charges $75/hr, is located in Madrid, Spain, speaks English and Spanish, has a 97% project completion rate, and maintains a 4.8/5 rating based on 64 reviews.",
        },
        {
            "query": "How does the recommendation system work on Shakers?",
            "expected_sources": ["finding_talent"],
            "expected_answer": "Shakers uses an AI-powered matching algorithm to analyze your project requirements and suggest the most suitable freelancers. The system evaluates factors such as skill relevance, past performance on similar projects, availability compatibility, and communication style preferences. You can also use advanced search filters to narrow down your talent search by specific skills, experience level, hourly rate, location, languages, and availability. For enterprise clients, Shakers offers dedicated account management and custom talent bench building to create pools of pre-vetted professionals for ongoing projects.",
        },
    ]

    with open(BENCHMARK_QUERIES_PATH, "w") as f:
        json.dump(benchmarks, f, indent=2)

    print(f"Generated {len(benchmarks)} benchmark queries in {BENCHMARK_QUERIES_PATH}")
    return benchmarks


def generate_user_profiles():
    """Generate simulated user profiles with query history."""
    # Define interests by category
    interests_by_category = {
        "development": [
            "web development",
            "mobile development",
            "frontend",
            "backend",
            "full-stack",
            "javascript",
            "python",
            "react",
            "angular",
            "vue",
            "node.js",
            "android",
            "ios",
            "cloud",
            "devops",
        ],
        "design": [
            "ui design",
            "ux design",
            "graphic design",
            "logo design",
            "web design",
            "mobile design",
            "illustration",
            "branding",
        ],
        "content": [
            "content writing",
            "copywriting",
            "technical writing",
            "blog posts",
            "seo writing",
            "editing",
            "proofreading",
            "translation",
        ],
        "marketing": [
            "digital marketing",
            "social media",
            "seo",
            "sem",
            "email marketing",
            "content marketing",
            "growth hacking",
            "advertising",
        ],
        "business": [
            "business consulting",
            "project management",
            "financial analysis",
            "legal consultation",
            "hr consulting",
            "virtual assistance",
        ],
        "platform": [
            "payments",
            "hiring",
            "contracts",
            "proposals",
            "reviews",
            "freelancer verification",
            "escrow",
            "fees",
            "invoicing",
        ],
    }

    # Define query templates by category
    query_templates_by_category = {
        "development": [
            "I need a {0} developer",
            "Looking for someone who knows {0}",
            "Help me find a {0} expert",
            "Need help with {0} development",
            "Who can build a {0} application?",
        ],
        "design": [
            "I need a {0} designer",
            "Looking for someone to design {0}",
            "Who can help with {0} design?",
            "Need a creative {0} specialist",
        ],
        "content": [
            "I need someone to write {0}",
            "Looking for a {0} writer",
            "Who can help create {0} content?",
            "Need help with {0} writing",
        ],
        "marketing": [
            "I need help with {0} marketing",
            "Looking for a {0} marketer",
            "Who can manage my {0} campaigns?",
            "Need assistance with {0} strategy",
        ],
        "business": [
            "I need a {0} consultant",
            "Looking for help with {0}",
            "Who can assist with {0} management?",
            "Need advice on {0}",
        ],
        "platform": [
            "How does {0} work on Shakers?",
            "What are the {0} policies?",
            "Tell me about {0} on the platform",
            "How to handle {0} on Shakers?",
        ],
    }

    # List of document IDs from knowledge base
    document_ids = [
        "api-documentation.md",
        "client-success-guide.md",
        "dispute-resolution.md",
        "enterprise-solutions.md",
        "freelancer-success-guide.md",
        "getting-started-guide.md",
        "industry-specific-guide.md",
        "platform-features.md",
        "project-creation-guide.md",
        "security-privacy.md",
        "skill-assessment-guide.md",
        "payments.md",
        "freelancers.md",
        "freelancer-profiles.md",
        "finding_talent.md",
        "shakers-technical-documentation.md",
    ]

    # Generate user profiles
    profiles = []
    for i in range(1, 11):  # Generate 10 user profiles
        # Select random interests from different categories
        user_interests = []
        for category in interests_by_category:
            if random.random() > 0.3:  # 70% chance to have interest in a category
                # Add 1-3 interests from this category
                n_interests = min(3, len(interests_by_category[category]))
                category_interests = random.sample(
                    interests_by_category[category], k=random.randint(1, n_interests)
                )
                user_interests.extend(category_interests)

        # Generate viewed documents
        num_viewed = random.randint(0, min(4, len(document_ids)))
        viewed_documents = random.sample(document_ids, k=num_viewed)

        # Generate query history based on interests
        queries = []
        num_queries = random.randint(3, 8)

        for _ in range(num_queries):
            # Select a random category
            category = random.choice(list(query_templates_by_category.keys()))

            # Select a random template from that category
            template = random.choice(query_templates_by_category[category])

            # Fill in the template with an interest
            if category in interests_by_category and interests_by_category[category]:
                interest = random.choice(interests_by_category[category])
                query = template.format(interest)
                queries.append(query)
            else:
                # Fallback if category has no interests (shouldn't happen)
                queries.append(f"Tell me about {category} on Shakers")

        # Create profile
        profile = {
            "user_id": f"user{i}",
            "interests": user_interests,
            "viewed_documents": viewed_documents,
            "queries": queries,
            "last_active": (
                datetime.now() - timedelta(days=random.randint(0, 30))
            ).isoformat(),
        }

        profiles.append(profile)

    with open(USER_PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)

    print(f"Generated {len(profiles)} user profiles in {USER_PROFILES_PATH}")
    return profiles


if __name__ == "__main__":
    print("Generating test data...")
    test_queries = generate_test_queries()
    benchmark_queries = generate_benchmark_queries()
    user_profiles = generate_user_profiles()
    print("Test data generation complete.")
    print(
        f"Total items generated: {len(test_queries) + len(benchmark_queries) + len(user_profiles)}"
    )
