import yt_dlp
import time
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import shutil

class CandidateVideoPoolGenerator:
    def __init__(self, max_results_per_term=15, output_dir="output"):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'max_downloads': max_results_per_term,
            'sleep_interval_requests': 3,  
            'sleep_interval': 3,    
            'max_sleep_interval': 4
        }
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.output_dir = output_dir
        self.comments_dir = os.path.join(self.output_dir, "comments")
        self.max_comment = 20

    def _sanitize_filename(self, text):
        return re.sub(r'[\\/*?:"<>|]', "_", text)[:50]  # tránh tên file quá dài hoặc chứa ký tự đặc biệt

    def _get_comments(self, url):
        try:
            with yt_dlp.YoutubeDL({
                'quiet': True,
                'extract_comments': True,
                'getcomments': True,
                'extractor_args': {
                    'youtube': {
                        'max_comments': [str(self.max_comment)],
                    }
                }
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                comments = [comment['text'] for comment in info.get('comments', [])[:1000]]

                # Lưu comment vào file riêng
                video_id = info.get('id', 'unknown')
                filename = f"comments_{self._sanitize_filename(video_id)}.json"
                filepath = os.path.join(self.comments_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(comments, f, ensure_ascii=False, indent=2)

                return comments
        except Exception as e:
            print(f"❌ Lỗi khi lấy bình luận {url}: {str(e)}")
            return []

    def _extract_video_info(self, entry):
        base_info = {
            'id': entry.get('id', ''),
            'title': entry.get('title', 'No Title'),
            'description': entry.get('description', ''),
            'url': entry.get('url', ''),
            'duration': entry.get('duration', 0),
            'view_count': entry.get('view_count', 0),
            'description': entry.get('description', ''),
            'tag': entry.get('tags', []),
            'category': entry.get('categories', []),
            'comment_file': None  
        }

        print(f"🔍 Đang xử lý video: {base_info['title']} ({base_info['duration']}s)")

        future = self.executor.submit(self._get_comments, entry['url'])
        comments = future.result(timeout=60)

        if comments:
            base_info['comment_file'] = f"comments_{self._sanitize_filename(base_info['id'])}.json"

        return base_info

    def generate_pool_old(self, search_terms):
        video_pool = []
        seen_urls = set()

        if not search_terms:
            print("⚠️ Không có từ khóa tìm kiếm")
            return []

        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            for idx, term in enumerate(search_terms, 1):
                try:
                    result = ydl.extract_info(
                        f"ytsearch{self.ydl_opts['max_downloads']}:{term}",
                        download=False
                    )
                    print(f"🔍 Tìm thấy {len(result.get('entries', []))} video")

                    for entry in result.get('entries', []):
                        if entry['url'] in seen_urls:
                            continue

                        try:
                            video_info = self._extract_video_info(entry)
                            video_pool.append(video_info)
                            seen_urls.add(entry['url'])
                            print(f"✅ Đã thêm: {video_info['title'][:30]}... (comments saved)")
                        except Exception as e:
                            print(f"❌ Lỗi xử lý entry: {str(e)}")

                except Exception as e:
                    print(f"⚠️ Lỗi tìm kiếm '{term}': {str(e)}")
                    continue

        self.executor.shutdown(wait=True)

        # Lưu toàn bộ video info vào file JSON
        video_file = os.path.join(self.output_dir, "video_pool.json")
        with open(video_file, "w", encoding="utf-8") as f:
            json.dump(video_pool, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 Tổng số video ứng viên: {len(video_pool)}")
        print(f"📁 Thông tin video đã lưu tại: {video_file}")
        print(f"📁 Bình luận lưu tại: {self.comments_dir}")
        return video_pool
    
    def generate_pool(self, search_terms):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.comments_dir, exist_ok=True)

        video_pool = []
        seen_urls = set()
        extract_futures = []

        if not search_terms:
            print("⚠️ Không có từ khóa tìm kiếm")
            return []

        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            for idx, term in enumerate(search_terms, 1):
                try:
                    print(f"\n📌 Từ khóa {idx}/{len(search_terms)}: '{term}'")
                    result = ydl.extract_info(
                        f"ytsearch{self.ydl_opts['max_downloads']}:{term}",
                        download=False
                    )
                    entries = result.get('entries', [])

                    for entry in entries:
                        if entry['url'] in seen_urls:
                            continue
                        seen_urls.add(entry['url'])

                        # Nộp job xử lý video vào thread pool
                        future = self.executor.submit(self._extract_video_info, entry)
                        extract_futures.append(future)

                except Exception as e:
                    print(f"⚠️ Lỗi tìm kiếm '{term}': {str(e)}")
                    continue

        for future in as_completed(extract_futures):
            try:
                video_info = future.result()
                video_pool.append(video_info)
                print(f"✅ Đã thêm: {video_info['title'][:30]}... (comments saved)")
            except Exception as e:
                print(f"❌ Lỗi xử lý video song song: {str(e)}")

        self.executor.shutdown(wait=True)

        video_file = os.path.join(self.output_dir, "video_pool.json")
        with open(video_file, "w", encoding="utf-8") as f:
            json.dump(video_pool, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 Tổng số video ứng viên: {len(video_pool)}")
        print(f"📁 Thông tin video đã lưu tại: {video_file}")
        print(f"📁 Bình luận lưu tại: {self.comments_dir}")
        return video_pool