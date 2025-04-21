from video_analyzer import SmartVideoAnalyzer
from keyword_generator import KeywordGenerator
from candidate_pool import CandidateVideoPoolGenerator
from utils import get_video_info

def analyze_and_generate_pool(video_url, api_key):
    analyzer = SmartVideoAnalyzer(api_key)
    result = analyzer.analyze(video_url)
    
    if not result:
        return []

    keyword_gen = KeywordGenerator(api_key)
    search_terms = keyword_gen.generate_search_terms(result['keywords'])

    pool_gen = CandidateVideoPoolGenerator()
    return pool_gen.generate_pool(search_terms)

def main():
    video_url = "https://www.youtube.com/watch?v=f8Z9JyB2EIE&t=3s"
    api_key = 'AIzaSyCHMeOtuunTH3t7BVigpSoD-qs3rHpuHQk'
    candidate_pool = analyze_and_generate_pool(video_url, api_key)
    print(f"Found {len(candidate_pool)} candidate videos")

if __name__ == "__main__":
    main()