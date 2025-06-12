import pandas as pd
import requests
import time
import re
import json
import random
from dotenv import load_dotenv
import os
import argparse
from datetime import datetime, timedelta
# from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration

# # kobart-title 모델 및 토크나이저 로드 (최초 1회만)
# tokenizer = PreTrainedTokenizerFast.from_pretrained("EbanLee/kobart-title")
# model = BartForConditionalGeneration.from_pretrained("EbanLee/kobart-title")

class RestaurantDataProcessor:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def clean_address_advanced(self, address):
        """강화된 주소 정제 함수"""
        if pd.isna(address) or address == "":
            return ""
        address = str(address).strip()
        
        # 층수, 호수, 상세 정보 제거
        patterns_to_remove = [
            r'\s*\d+층.*$',
            r'\s*지하\d+층.*$', 
            r'\s*\d+호.*$',
            r'\s*[가-힣]+\s*\d+호.*$',
            r'\s*[A-Za-z0-9\s]+호.*$',
            r'\s*[A-Za-z0-9\s]+동.*$',
        ]
        
        for pattern in patterns_to_remove:
            address = re.sub(pattern, '', address)
            
        # 도로명 + 번지 이후의 모든 내용 제거
        road_patterns = [
            r'(.*?(?:길|로|대로|거리|가)\s*\d+(?:-\d+)?)',
            r'(.*?(?:길|로|대로|거리|가)\s*\d+[가-힣]*)',
        ]
        
        for pattern in road_patterns:
            match = re.match(pattern, address)
            if match:
                return match.group(1).strip()
                
        # 마지막 숫자 이후의 모든 내용 제거
        number_pattern = r'(.*\d+)'
        match = re.match(number_pattern, address)
        if match:
            return match.group(1).strip()
            
        return address.strip()
    
    def try_geocoding(self, address):
        """단일 주소로 지오코딩 시도"""
        apiurl = "https://api.vworld.kr/req/address"
        
        params = {
            "service": "address",
            "request": "getcoord", 
            "crs": "epsg:4326",
            "address": address,
            "format": "json",
            "type": "road",
            "key": self.api_key
        }
        
        try:
            response = requests.get(apiurl, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['response']['status'] == 'OK':
                    point = data['response']['result']['point']
                    return float(point['y']), float(point['x']), "성공"
                    
            # 지번 주소로 재시도
            params['type'] = 'parcel'
            response = requests.get(apiurl, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['response']['status'] == 'OK':
                    point = data['response']['result']['point']
                    return float(point['y']), float(point['x']), "성공"
                    
            return None, None, data.get('response', {}).get('status', 'UNKNOWN_ERROR')
        except Exception as e:
            return None, None, f"예외: {str(e)}"
    
    def get_coordinates_with_fallback(self, address, gu_name):
        """여러 방법으로 좌표를 얻는 함수"""
        if pd.isna(address) or address == "":
            return None, None, "빈 주소"
        
        status = "시도 안함"
            
        # 방법 1: 정제된 주소로 시도
        cleaned = self.clean_address_advanced(address)
        if cleaned != address:
            lat, lng, status = self.try_geocoding(cleaned)
            if lat is not None:
                return lat, lng, "정제된 주소 성공"
                
        # 방법 2: 더 간단하게 정제
        simple_address = self.extract_simple_address(address, gu_name)
        if simple_address:
            lat, lng, status = self.try_geocoding(simple_address)
            if lat is not None:
                return lat, lng, "간단 주소 성공"
                
        return None, None, f"모든 방법 실패: {status}"
    
    def extract_simple_address(self, address, gu_name):
        """매우 간단한 주소 추출"""
        simple_pattern = fr'(서울\s*{gu_name}\s*[가-힣]+(?:로|길|대로))'
        match = re.search(simple_pattern, address)
        if match:
            return match.group(1)
        return None
    
    def remove_non_food_categories(self, df):
        """음식과 관련 없는 카테고리 제거"""
        non_food_categories = [
            '자동차', '세탁소', '심리상담', '영어회화', '스포츠용품', '컨설팅', 
            '취미,레저용품', '안경원', '수입의류', '귀금속,시계', '요가원', 
            '오피스텔', '문,창문', '입시교육', '골프용품', '무용,발레', '의류대여', 
            '왁싱,제모', '안과', '신복관', '모델 에이전시', '중개업', '글쓰기,독서지도',
            '척추,자세교정', '피아노', '미용교육', '이벤트,파티', '방송프로그램제작,공급',
            '고시원,고시텔', '나무제품제조', '결혼예물', '전문사진촬영,처리',
            '가구,인테리어', '해우리', '별관,부속', '3급', '수학교육', '오디오출판,원판녹음',
            '정보 없음', '주방용품', '웨딩컨설팅,플래너', '도서관', '화장품,향수', 
            '드럭스토어', '임대업', '벽지,장판,마루', '모텔', '전시,판매', '경영컨설팅',
            '남성정장', '실내골프연습장', '광고대행', '문구,팬시용품', '산부인과', 
            '노래방', '목욕탕,사우나', '병원,의원', '테마카페', '교습학원,교습소', 
            '필라테스', '스크린골프장', '키즈카페,실내놀이터', '플라워카페', '한의원',
            '영화관', '셀프,대여스튜디오', '프랜차이즈본사', '속눈썹증모,연장',
            '종합패션', '스포츠시설', '복합문화공간', '여성의류', '소프트웨어개발',
            '애견카페', '웨딩드레스,예복', '공방', '메이크업', '아파트', '종합도소매',
            '갤러리,화랑', '방탈출카페', '인테리어디자인', '꽃집,꽃배달', '패션',
            '치과', '정형외과', '어린이집', '주택', '운세,사주', '사진,스튜디오',
            '네일아트,네일샵', '성형외과', '기업,빌딩', '피부과', '보드카페',
            '피부,체형관리', '장소대여', '예식장', '4성급', '복권,로또', '1성급',
            '가전제품수리', '고양이카페', '비뇨의학과', '요가,명상', '화장품제조',
            '한방카페', '예술품,골동품', '이비인후과', '연구,연구소', '경호,보안',
            '전문디자인', '찜질방', '인테리어소품', '경기장', '행사', '광고,마케팅',
            '전문건설업', '5성급', '인터넷방송', '설계,엔지니어링', '애플스토어',
            '출장요리', '산후조리원', '시각디자인', '철물점', '건강검진', '가구',
            '캐주얼웨어', '쉐어하우스,하숙', '장난감', '건축설계', 'CCTV', '산',
            '원단,섬유,직물', '주간신문', '수영용품', '배달대행', '수제화', '안마,마사지',
            '무역', '한일관', '호텔', '상품권판매', '클럽', '펄프,종이제조', '조경건설',
            '거리,골목', '목욕,찜질', '공연장', '가정의학과', '재봉틀,미싱', '약국',
            '실외골프연습장', '스터디카페', '게이트나인', '오락실', '미용', '사주카페',
            '암벽등반', '스포츠,오락', '반려동물호텔', '엔터테인먼트', '정보통신,IT',
            '배급업', '드럼', '건강기능보조식품', '지원,대행', '기능성화장품',
            '취미교육', '식물원,수목원', '개발,공급업', '생활협동조합', '머리염색',
            '금제품전문', '슈퍼,마트', '아동,청소년상담', '리스', '수입가구', '밀키트',
            '방앗간', '폐백,이바지음식', '반려동물분양', '2성급', '신발', '정육점',
            '당구장', '편의점', '식품', '헬스장', '식료품', '미술교육', '개신교',
            '가방,핸드백', '요리교육', '만화방', '수입식품', '영어교육', '유흥주점',
            '육류가공,제조', '한복'
        ]
        
        pattern = '|'.join(non_food_categories)
        return df[~df['카테고리'].str.contains(pattern, na=False)]
    
    def remove_duplicates_smart(self, df):
        """중복 제거 (더 많은 정보를 가진 행 우선 유지)"""
        df_temp = df.copy()
        df_temp['info_count'] = df_temp.notna().sum(axis=1)
        
        df_result = df_temp.loc[df_temp.groupby(['음식점_이름', '주소'])['info_count'].idxmax()]
        df_result = df_result.drop('info_count', axis=1)
        
        return df_result
    
    def filter_gu_only(self, df, gu_name):
        """특정구 데이터만 필터링"""
        return df[df['주소'].str.contains(gu_name, na=False)].copy().reset_index(drop=True)

    
    def format_time_range(self, time_str):
        """시간 범위를 오전/오후 형식으로 변환"""
        if not time_str or pd.isna(time_str):
            return "정보 없음"
            
        time_str = str(time_str).strip()
        
        # 라스트오더, 브레이크타임 제거
        time_str = re.sub(r';\\s*\\d{1,2}:\\d{2}\\s*라스트오더', '', time_str)
        time_str = re.sub(r'라스트오더.*', '', time_str)
        time_str = re.sub(r'브레이크타임.*', '', time_str)
        time_str = time_str.strip()
        
        # 시간 패턴 찾기
        time_pattern = r'(\\d{1,2}):(\\d{2})\\s*-\\s*(\\d{1,2}):(\\d{2})'
        match = re.search(time_pattern, time_str)
        
        if match:
            start_hour, start_min, end_hour, end_min = match.groups()
            start_hour, end_hour = int(start_hour), int(end_hour)
            
            # 오전/오후 변환
            start_period = "오전" if start_hour < 12 else "오후"
            end_period = "오전" if end_hour < 12 else "오후"
            
            # 12시간 형식으로 변환
            start_display = start_hour
            end_display = end_hour
            
            if start_hour == 0:
                start_display = 12
                start_period = "오전"
            elif start_hour > 12:
                start_display = start_hour - 12
                start_period = "오후"
            elif start_hour == 12:
                start_period = "오후"
                
            if end_hour == 0:
                end_display = 12
                end_period = "오전"
            elif end_hour > 12:
                end_display = end_hour - 12
                end_period = "오후"
            elif end_hour == 12:
                end_period = "오후"
                
            return f"{start_period} {start_display}:{start_min}~{end_period} {end_display}:{end_min}"
            
        return "정보 없음"
    
    def convert_business_hours(self, hours_text):
        """영업시간을 요일별 JSON 형식으로 변환"""
        result = {
            '월요일': '정보 없음', '화요일': '정보 없음', '수요일': '정보 없음',
            '목요일': '정보 없음', '금요일': '정보 없음', '토요일': '정보 없음', '일요일': '정보 없음'
        }
        
        if pd.isna(hours_text) or not hours_text or str(hours_text).strip() == "":
            return json.dumps(result, ensure_ascii=False)
            
        hours_text = str(hours_text).strip()
        
        # "매일:" 패턴 처리
        if "매일:" in hours_text:
            time_part = hours_text.replace("매일:", "").strip()
            formatted_time = self.format_time_range(time_part)
            for day in result.keys():
                result[day] = formatted_time if formatted_time != "정보 없음" else '정보 없음'
            return json.dumps(result, ensure_ascii=False)
            
        # 요일별 처리
        day_mapping = {
            '월': '월요일', '화': '화요일', '수': '수요일', '목': '목요일',
            '금': '금요일', '토': '토요일', '일': '일요일'
        }
        
        parts = hours_text.split(';')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            for day_abbr, day_full in day_mapping.items():
                if part.startswith(day_abbr + ':'):
                    time_part = part.replace(day_abbr + ':', '').strip()
                    
                    if '휴무' in time_part or '정기휴무' in time_part:
                        result[day_full] = '휴무일'
                    else:
                        formatted_time = self.format_time_range(time_part)
                        result[day_full] = formatted_time if formatted_time != "정보 없음" else '정보 없음'
                    break
                    
        return json.dumps(result, ensure_ascii=False)
    
    def add_created_time_to_review(self, review_str):
        """리뷰에 작성 시간 추가"""
        try:
            reviews = json.loads(review_str)
            
            for review in reviews:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                random_date = start_date + timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                review['작성시간'] = random_date.strftime('%Y-%m-%dT%H:%M:%S')
                
            return json.dumps(reviews, ensure_ascii=False)
            
        except (json.JSONDecodeError, TypeError):
            return review_str
    
    # def add_titles_to_review(self, review_str):
    #     """리뷰 리스트 내 각 게시글에 kobart-title 기반 제목 생성 추가"""
    #     try:
    #         reviews = json.loads(review_str)
    #         for review in reviews:
    #             post = review.get('게시글', '')
    #             # 게시글이 비어있으면 제목도 빈 문자열
    #             if not post or not isinstance(post, str) or post.strip() == "":
    #                 review['제목'] = ""
    #                 continue
    #             # kobart-title로 제목 생성
    #             input_ids = tokenizer.encode(post, return_tensors="pt", max_length=1024, truncation=True)
    #             summary_ids = model.generate(
    #                 input_ids=input_ids,
    #                 bos_token_id=model.config.bos_token_id,
    #                 eos_token_id=model.config.eos_token_id,
    #                 length_penalty=1.0,
    #                 max_length=40,
    #                 min_length=3,
    #                 num_beams=6,
    #                 repetition_penalty=1.5,
    #             )
    #             title = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    #             title = re.sub(r'\[.*?\]', '', title).strip()
    #             review['제목'] = title
    #         return json.dumps(reviews, ensure_ascii=False)
    #     except Exception as e:
    #         # 파싱 실패 시 원본 반환
    #         return review_str

    def process_complete_pipeline(self, input_file, output_file, gu_name):
        """전체 파이프라인 실행"""
        print("=== 음식점 데이터 전체 처리 시작 ===")
        
        # 1. 데이터 로드
        print("1. 데이터 로딩 중...")
        df = pd.read_csv(input_file)
        print(f"   초기 데이터: {len(df)}개")
        
        # 2. 결측치 확인
        print("2. 결측치 확인 중...")
        cols_to_check = ['음식점_이름', '카테고리', '주소']
        missing_count = df[cols_to_check].isnull().sum().sum()
        print(f"   주요 컬럼 결측치: {missing_count}개")
        
        # 3. 비음식 카테고리 제거
        print("3. 비음식 카테고리 제거 중...")
        df = self.remove_non_food_categories(df)
        print(f"   필터링 후 데이터: {len(df)}개")
        
        # 4. 중복 제거
        print("4. 중복 제거 중...")
        df = self.remove_duplicates_smart(df)
        print(f"   중복 제거 후 데이터: {len(df)}개")
        
        # 5. 특정 구만 필터링
        print("5. 데이터만 필터링 중...")
        df = self.filter_gu_only(df, gu_name)
        print(f"   데이터: {len(df)}개")
        
        # 6. 영업시간 정제 (정보 없음 → 기본값)
        print("6. 영업시간 기본값 설정 중...")
        default_hours = "월: 11:00 - 21:00; 화: 11:00 - 21:00; 수: 11:00 - 21:00; 목: 11:00 - 21:00; 금: 11:00 - 21:00; 토: 11:00 - 21:00; 일: 11:00 - 21:00;"
        df['영업시간'] = df['영업시간'].replace('정보 없음', default_hours)
        
        # 7. 지오코딩 (좌표 추가)
        print("7. 지오코딩 진행 중...")
        df['위도'] = None
        df['경도'] = None
        df['지오코딩_상태'] = None
        
        success_count = 0
        for index, row in df.iterrows():
            address = row['주소']
            lat, lng, status = self.get_coordinates_with_fallback(address, gu_name)
            
            df.at[index, '위도'] = lat
            df.at[index, '경도'] = lng
            df.at[index, '지오코딩_상태'] = status
            
            if lat is not None:
                success_count += 1
                
            if (index + 1) % 100 == 0:
                current_success_rate = success_count / (index + 1) * 100
                print(f"   진행률: {index + 1}/{len(df)} ({(index + 1)/len(df)*100:.1f}%) - 성공률: {current_success_rate:.1f}%")
                
            time.sleep(0.15)
        
        print(f"   지오코딩 성공률: {success_count/len(df)*100:.1f}%")
        
        # 8. 영업시간 JSON 변환
        print("8. 영업시간 JSON 형식 변환 중...")
        df['영업시간'] = df['영업시간'].apply(self.convert_business_hours)
        
        # 9. 리뷰에 작성시간 추가
        print("9. 리뷰에 작성시간 추가 중...")
        df['리뷰'] = df['리뷰'].apply(self.add_created_time_to_review)

        # # 10. 제목 추출
        # print("10. 리뷰에 제목 생성 중...")
        # df['리뷰'] = df['리뷰'].apply(self.add_titles_to_review)
        
        # 11. 불필요한 컬럼 제거
        print("11. 최종 정리 중...")
        columns_to_drop = ['지오코딩_상태']
        df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
        
        # 12. 결과 저장
        print("12. 결과 저장 중...")
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n=== 처리 완료 ===")
        print(f"최종 데이터: {len(df)}개")
        print(f"저장 위치: {output_file}")
        
        return df

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description='특정 구 음식점 데이터 처리 파이프라인')
    parser.add_argument('--api-key', type=str, default=None, help='VWorld API Key (환경변수 VWORLD_API_KEY 기본값)')
    parser.add_argument('--input', '-i', type=str, required=True, help='입력 CSV 파일 경로')
    parser.add_argument('--output', '-o', type=str, required=True, help='출력 CSV 파일 경로')
    parser.add_argument('--gu', type=str, required=False, default='관악구', help='필터링할 구 이름 (예: 관악구, 동작구 등)')
    args = parser.parse_args()

    # 우선순위: 명령줄 인자 > 환경변수
    api_key = args.api_key or os.getenv("VWORLD_API_KEY")
    if not api_key:
        raise ValueError("API 키가 필요합니다. --api-key 옵션 또는 VWORLD_API_KEY 환경변수를 설정하세요.")

    processor = RestaurantDataProcessor(api_key)

    try:
        result_df = processor.process_complete_pipeline(args.input, args.output, args.gu)
        print("\n처리가 성공적으로 완료되었습니다!")
        print("\n=== 결과 미리보기 ===")
        print(f"컬럼: {list(result_df.columns)}")
        print(f"샘플 데이터:")
        print(result_df[['음식점_이름', '카테고리', '주소', '위도', '경도']].head())
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()