import yt_dlp
import time
from concurrent.futures import ThreadPoolExecutor

class CandidateVideoPoolGenerator:
    def __init__(self, max_results_per_term=5):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'max_downloads': max_results_per_term,
            'getcomments': True,  # Bật tính năng lấy bình luận
            'extract_comments': True,  # Trích xuất bình luận
            'comments_max': 10,  # Giới hạn tối đa 100 bình luận
            'sleep_interval_requests': 1  # Giảm áp lực request
        }
        self.executor = ThreadPoolExecutor(max_workers=4)  # Xử lý song song

    def _get_comments(self, url):
        """Lấy bình luận với cấu hình tối ưu"""
        try:
            with yt_dlp.YoutubeDL({
                'quiet': True,
                'extract_comments': True,
                'getcomments': True,
                'comments_max': 10,
                'sleep_interval_requests': 2,
                'ignoreerrors': True
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                return [comment['text'] for comment in info.get('comments', [])[:100]]
        except Exception as e:
            print(f"❌ Lỗi khi lấy bình luận {url}: {str(e)}")
            return []

    def _extract_video_info(self, entry):
        """Trích xuất thông tin video + bình luận"""
        base_info = {
            'title': entry.get('title', 'No Title'),
            'description': entry.get('description', ''),
            'url': entry.get('url', ''),
            'duration': entry.get('duration', 0),
            'view_count': entry.get('view_count', 0),
            'comments': []  # Khởi tạo danh sách bình luận
        }
        
        # Lấy bình luận bất đồng bộ
        future = self.executor.submit(self._get_comments, entry['url'])
        base_info['comments'] = future.result(timeout=30)  # Timeout 30s
        
        return base_info

    def generate_pool(self, search_terms):
        video_pool = []
        seen_urls = set()
        
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

                    for entry in result.get('entries', []):
                        if entry['url'] in seen_urls:
                            continue
                            
                        try:
                            video_info = self._extract_video_info(entry)
                            video_pool.append(video_info)
                            seen_urls.add(entry['url'])
                            print(f"✅ Đã thêm: {video_info['title'][:30]}... ({len(video_info['comments'])} bình luận)")
                        except Exception as e:
                            print(f"❌ Lỗi xử lý entry: {str(e)}")

                except Exception as e:
                    print(f"⚠️ Lỗi tìm kiếm '{term}': {str(e)}")
                    continue

        self.executor.shutdown(wait=True)
        print(f"\n🎉 Tổng số video ứng viên: {len(video_pool)}")
        return video_pool