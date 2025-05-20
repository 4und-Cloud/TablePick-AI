import json
import time
import random
import os
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, List, Optional, Union, Any


class NaverMapCrawler:
    """네이버 지도 음식점 정보 크롤러 클래스"""
    
    def __init__(self, headless: bool = False, timeout: int = 3):
        """
        크롤러 초기화
        
        Args:
            headless: 헤드리스 모드 활성화 여부
            timeout: 웹 요소 대기 시간(초)
        """
        self.timeout = timeout
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')

        # USB 오류 로그 메시지 숨기기
        self.options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if headless:
            self.options.add_argument('--headless=new')
        
        self.driver = None
        self.wait = None
    
    def _initialize_driver(self):
        """Selenium 드라이버 초기화"""
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.wait = WebDriverWait(self.driver, self.timeout)
    
    def _close_driver(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
    
    @staticmethod
    def safe_find_element(driver, by, selector, default="정보 없음", attribute=None):
        """단일 요소를 안전하게 추출"""
        try:
            element = driver.find_element(by, selector)
            return element.get_attribute(attribute).strip() if attribute else element.text.strip()
        except Exception:
            return default
    
    @staticmethod
    def safe_find_elements(driver, by, selector, attribute=None):
        """다중 요소를 안전하게 추출"""
        try:
            elements = driver.find_elements(by, selector)
            if attribute:
                return [el.get_attribute(attribute) for el in elements if el.get_attribute(attribute)]
            return [el.text.strip() for el in elements if el.text.strip()]
        except Exception:
            return []
    
    @staticmethod
    def scroll_to_load(driver, max_scrolls=10, pause_time=0.2):
        """페이지 끝까지 스크롤하며 콘텐츠 로드"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def search_restaurant(self, restaurant_name: str, district: str = "강남구") -> bool:
        """
        음식점 검색 및 상세 페이지로 이동
        
        Args:
            restaurant_name: 음식점 이름
            district: 검색할 지역구
            
        Returns:
            bool: 검색 성공 여부
        """
        search_url = f"https://map.naver.com/p/search/{restaurant_name} {district}"
        
        try:
            self.driver.get(search_url)
            
            # 검색 결과 iframe 진입 시도
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe")))
            except:
                # 검색 결과 iframe 진입
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe")))
                self.driver.switch_to.frame("searchIframe")
                
                # 음식점 이름에서 괄호 이전 부분만 추출하여 검색
                short_name = re.split(r'\s*\(', restaurant_name)[0]
                target_xpath = f"//a[@role='button'][.//span[contains(text(), '{short_name}')]]"
                
                try:
                    first_result = self.driver.find_element(By.XPATH, target_xpath)
                    first_result.click()
                except Exception as e:
                    print(f"검색 결과에서 '{restaurant_name}'을 찾거나 클릭할 수 없습니다: {e}")
                    return False
                
                self.driver.switch_to.default_content()
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe")))
            
            self.driver.switch_to.frame("entryIframe")
            return True
            
        except Exception as e:
            print(f"음식점 검색 중 오류 발생: {e}")
            return False
    
    def extract_basic_info(self) -> Dict[str, str]:
        """기본 음식점 정보 추출"""
        data = {
            '음식점_이름': self.safe_find_element(self.driver, By.CSS_SELECTOR, "span.GHAhO"),
            '음식점_사진': self.safe_find_element(self.driver, By.CSS_SELECTOR, "div.fNygA img", attribute="src"),
            '주소': self.safe_find_element(self.driver, By.CSS_SELECTOR, "span.LDgIH"),
            '카테고리': self.safe_find_element(self.driver, By.CSS_SELECTOR, "span.lnJFt"),
            '전화번호': self.safe_find_element(self.driver, By.CSS_SELECTOR, "span.xlx7Q")
        }
        return data
    
    def extract_opening_hours(self) -> str:
        """영업시간 정보 추출"""
        try:
            if not self.driver.find_elements(By.CSS_SELECTOR, "div.H3ua4"):
                self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.gKP9i.RMgN0"))).click()
            
            openhour_rows = self.driver.find_elements(By.CSS_SELECTOR, "span.A_cdD")
            openhours = []
            
            for row in openhour_rows:
                try:
                    day = self.safe_find_element(row, By.CSS_SELECTOR, "span.i8cJw")
                    hours = self.safe_find_element(row, By.CSS_SELECTOR, "div.H3ua4").replace('\n', '; ')
                    openhours.append(f"{day}: {hours}")
                except Exception:
                    continue
            
            return "; ".join(openhours) if openhours else "정보 없음"
        except Exception:
            return "정보 없음"
    
    def extract_reviews(self, max_reviews: int = 50) -> List[Dict[str, Any]]:
        """리뷰 데이터 추출"""
        try:
            # 리뷰 탭으로 이동
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='리뷰']"))).click()
            time.sleep(1.0)
            
            # 리뷰 로딩 대기
            retry_count = 0
            max_retries = 10
            while retry_count < max_retries:
                review_lis = self.driver.find_elements(By.CSS_SELECTOR, "li.place_apply_pui.EjjAW")
                if review_lis:
                    break
                time.sleep(0.5)
                retry_count += 1
                print(f"리뷰 로딩 대기 중... ({retry_count}/{max_retries})")
            
            # 리뷰가 없는 경우 확인
            no_review_msg = self.driver.find_elements(By.XPATH, "//div[contains(text(), '리뷰가 없습니다')]")
            if no_review_msg or not review_lis:
                print("리뷰가 없습니다.")
                return []
            
            # 리뷰 데이터 수집
            review_data = []
            batch_size = 10
            
            while len(review_data) < max_reviews:
                all_reviews = self.driver.find_elements(By.CSS_SELECTOR, "li.place_apply_pui.EjjAW")
                remaining_reviews = all_reviews[len(review_data):min(len(review_data) + batch_size, max_reviews)]
                
                if not remaining_reviews:
                    break
                
                batch_data = []
                for li in remaining_reviews:
                    try:
                        # 리뷰 요소로 스크롤
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", li)
                        time.sleep(0.5)
                        
                        # 게시글 더보기 버튼 클릭
                        post_more_btn = li.find_elements(By.CSS_SELECTOR, "a[data-pui-click-code='rvshowmore']")
                        if post_more_btn:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", post_more_btn[0])
                            time.sleep(0.1)
                            self.driver.execute_script("arguments[0].click();", post_more_btn[0])
                            time.sleep(0.7)
                        
                        # 데이터 추출
                        tags = self.safe_find_elements(li, By.CSS_SELECTOR, "div.pui__HLNvmI span.pui__jhpEyP")
                        post = self.safe_find_element(li, By.CSS_SELECTOR, "div.pui__vn15t2 span, div.pui__vn15t2")
                        
                        if post == "정보 없음":
                            post = self.safe_find_element(li, By.CSS_SELECTOR, "a[data-pui-click-code='rvshowmore']")
                        
                        images = self.safe_find_elements(li, By.CSS_SELECTOR, "div.HH5sZ img", attribute="src")[:3]
                        keywords = self.safe_find_elements(li, By.CSS_SELECTOR, "div.pui__-0Ter1 span em")
                        
                        batch_data.append({
                            "태그": tags,
                            "게시글": post,
                            "이미지": images,
                            "키워드": keywords
                        })
                    except Exception as e:
                        print(f"리뷰 데이터 처리 중 오류: {e}")
                        continue
                
                review_data.extend(batch_data)
                
                # 다음 리뷰 로드
                more_btn = self.driver.find_elements(By.CSS_SELECTOR, "a.fvwqf")
                if more_btn:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", more_btn[0])
                    time.sleep(0.2)
                    self.driver.execute_script("arguments[0].click();", more_btn[0])
                    time.sleep(1.0)
                else:
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(0.5)
                
                # 새로운 리뷰가 로드되었는지 확인
                new_review_count = len(self.driver.find_elements(By.CSS_SELECTOR, "li.place_apply_pui.EjjAW"))
                if new_review_count <= len(review_data):
                    print("더 이상 새로운 리뷰가 없습니다.")
                    break
            
            return review_data
            
        except Exception as e:
            print(f"리뷰 추출 중 오류: {e}")
            return []
    
    def extract_menu_info(self) -> List[Dict[str, str]]:
        """메뉴 정보 추출"""
        try:
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '메뉴')]"))).click()
            time.sleep(0.2)
            self.scroll_to_load(self.driver, max_scrolls=5, pause_time=0.1)
            
            menus = []
            for selector in [("li.order_list_item", "div.tit", "div.price > strong"), 
                            ("li.E2jtL", "span.lPzHi", "div.GXS1X em")]:
                items = self.driver.find_elements(By.CSS_SELECTOR, selector[0])
                for item in items:
                    name = self.safe_find_element(item, By.CSS_SELECTOR, selector[1])
                    price = self.safe_find_element(item, By.CSS_SELECTOR, selector[2])
                    if name != "정보 없음" and price != "정보 없음":
                        menus.append({"메뉴명": name, "가격": price})
            
            # 중복 제거
            unique = set()
            deduped_menus = [menu for menu in menus 
                            if not (menu['메뉴명'], menu['가격']) in unique 
                            and not unique.add((menu['메뉴명'], menu['가격']))]
            
            return deduped_menus
        except Exception as e:
            print(f"메뉴 정보 추출 중 오류: {e}")
            return []
    
    def get_restaurant_data(self, restaurant_name: str, district: str = "강남구") -> Optional[Dict[str, Any]]:
        """
        음식점 정보 크롤링 메인 함수
        
        Args:
            restaurant_name: 음식점 이름
            district: 검색할 지역구
            
        Returns:
            Dict 또는 None: 크롤링된 음식점 정보
        """
        try:
            self._initialize_driver()
            
            if not self.search_restaurant(restaurant_name, district):
                return None
            
            # 기본 정보 추출
            data = self.extract_basic_info()
            
            # 영업시간 추출
            data['영업시간'] = self.extract_opening_hours()
            
            # 리뷰 추출
            review_data = self.extract_reviews()
            data['리뷰'] = json.dumps(review_data, ensure_ascii=False)
            
            # 메뉴 정보 추출
            menu_data = self.extract_menu_info()
            data['메뉴_정보'] = json.dumps(menu_data, ensure_ascii=False)
            
            return data
            
        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            return None
        finally:
            self._close_driver()


class RestaurantDataCollector:
    """음식점 데이터 수집 클래스"""
    
    def __init__(self, output_path: str, district: str = "강남구"):
        """
        데이터 수집기 초기화
        
        Args:
            output_path: 결과 CSV 파일 경로
            district: 검색할 지역구
        """
        self.output_path = output_path
        self.district = district
        self.crawler = NaverMapCrawler(headless=False)
        
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    def collect_restaurants(self, restaurants_df: pd.DataFrame, start_idx: int, end_idx: int):
        """
        여러 음식점 정보 수집
        
        Args:
            restaurants_df: 음식점 목록이 있는 DataFrame
            start_idx: 시작 인덱스
            end_idx: 종료 인덱스
        """
        for i in range(start_idx, end_idx + 1):
            name = restaurants_df.loc[i, '음식점명']
            print('*' * 50)
            print(f'{i}번째 음식점: {name} 수집 시작')
            
            try:
                data = self.crawler.get_restaurant_data(name, self.district)
                
                if data:
                    df_one = pd.DataFrame([data])
                    # 파일 존재 여부 확인
                    header = not os.path.exists(self.output_path)
                    # DataFrame을 CSV로 저장
                    df_one.to_csv(self.output_path, mode='a', header=header, index=False, encoding='utf-8-sig')
                    print(f'{i}번째 음식점: {name} 저장 완료')
                else:
                    print(f'{i}번째 음식점: {name} 데이터 없음')
                
            except Exception as e:
                print(f'오류 발생: {e} → {i}번째 음식점: {name} 수집 실패')
            
            # 요청 간 딜레이
            time.sleep(random.uniform(3, 5))


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='네이버 지도 음식점 정보 크롤러')
    parser.add_argument('--input', '-i', type=str, required=True, help='음식점 목록 CSV 파일 경로')
    parser.add_argument('--output', '-o', type=str, required=True, help='결과 CSV 파일 경로')
    parser.add_argument('--district', '-d', type=str, default='강남구', help='검색할 지역구')
    parser.add_argument('--start', '-s', type=int, default=0, help='시작 인덱스')
    parser.add_argument('--end', '-e', type=int, help='종료 인덱스')
    
    args = parser.parse_args()
    
    # 음식점 목록 로드
    try:
        restaurants_df = pd.read_csv(args.input, encoding='utf-8')
        print(f"음식점 목록 로드 완료: {len(restaurants_df)}개 항목")
    except Exception as e:
        print(f"음식점 목록 로드 실패: {e}")
        return
    
    # 종료 인덱스가 지정되지 않은 경우 마지막 인덱스 사용
    end_idx = args.end if args.end is not None else len(restaurants_df) - 1
    
    # 데이터 수집기 초기화 및 실행
    collector = RestaurantDataCollector(args.output, args.district)
    collector.collect_restaurants(restaurants_df, args.start, end_idx)
    
    print(f"데이터 수집 완료: {args.start}~{end_idx}")


if __name__ == "__main__":
    main()
