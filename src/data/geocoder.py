import pandas as pd
import requests
import time
import re

def clean_address_advanced(address):
    """
    더 강화된 주소 정제 함수
    """
    if pd.isna(address) or address == "":
        return ""
    
    address = str(address).strip()
    
    # 1단계: 기본 정제
    # 층수, 호수, 상세 정보 제거
    patterns_to_remove = [
        r'\s*\d+층.*$',
        r'\s*지하\d+층.*$',
        r'\s*\d+호.*$',
        r'\s*[가-힣]+\s*\d+호.*$',
        r'\s*[A-Za-z0-9\s]+호.*$',
        r'\s*[A-Za-z0-9\s]+동.*$',  # 불필요한 동 정보 제거(예: "A동")
    ]
    
    for pattern in patterns_to_remove:
        address = re.sub(pattern, '', address)
    
    # 2단계: 상호명 및 기타 상세 정보 제거
    # 도로명 + 번지 이후의 모든 내용 제거
    road_patterns = [
        r'(.*?(?:길|로|대로|거리|가)\s*\d+(?:-\d+)?)',  # 기본 도로명 + 번지
        r'(.*?(?:길|로|대로|거리|가)\s*\d+[가-힣]*)',   # 번지 + 한글
    ]
    
    for pattern in road_patterns:
        match = re.match(pattern, address)
        if match:
            return match.group(1).strip()
    
    # 3단계: 건물명이나 상세 정보가 많은 경우 더 적극적으로 제거
    # 마지막 숫자 이후의 모든 내용 제거
    number_pattern = r'(.*\d+)'
    match = re.match(number_pattern, address)
    if match:
        return match.group(1).strip()
    
    return address.strip()

def get_coordinates_with_fallback(address, api_key):
    """
    여러 방법으로 좌표를 얻는 함수
    """
    if pd.isna(address) or address == "":
        return None, None, "빈 주소"
    
    status = "시도 안함"

    # 방법 1: 정제된 주소로 시도
    cleaned = clean_address_advanced(address)
    if cleaned != address:
        lat, lng, status = try_geocoding(cleaned, api_key)
        if lat is not None:
            return lat, lng, "정제된 주소 성공"
    
    # 방법 2: 더 간단하게 정제 (구 + 동/로 까지만)
    simple_address = extract_simple_address(address)
    if simple_address:
        lat, lng, status = try_geocoding(simple_address, api_key)
        if lat is not None:
            return lat, lng, "간단 주소 성공"
    
    return None, None, f"모든 방법 실패: {status}"

def try_geocoding(address, api_key):
    """
    단일 주소로 지오코딩 시도
    """
    apiurl = "https://api.vworld.kr/req/address"
    
    # 도로명 주소로 시도
    params = {
        "service": "address",
        "request": "getcoord",
        "crs": "epsg:4326",
        "address": address,
        "format": "json",
        "type": "road",
        "key": api_key
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

def extract_simple_address(address):
    """
    매우 간단한 주소 추출 (구 + 주요 도로명만)
    """
    # 강남구 + 주요 도로명까지만 추출
    simple_pattern = r'(서울\s*강남구\s*[가-힣]+(?:로|길|대로))'
    match = re.search(simple_pattern, address)
    if match:
        return match.group(1)
    return None

def add_coordinates_robust(input_file, output_file, address_column, api_key):
    """
    강화된 좌표 변환 함수
    """
    df = pd.read_csv(input_file)
    
    if address_column not in df.columns:
        raise ValueError(f"'{address_column}' 컬럼이 CSV 파일에 없습니다.")
    
    print(f"총 {len(df)}개의 주소를 처리합니다...")
    
    # 결과 컬럼 초기화
    df['위도'] = None
    df['경도'] = None
    df['지오코딩_상태'] = None
    df['정제된_주소'] = None
    
    success_count = 0
    
    for index, row in df.iterrows():
        address = row[address_column]
        
        # 좌표 변환 시도
        lat, lng, status = get_coordinates_with_fallback(address, api_key)
        
        # 결과 저장
        df.at[index, '위도'] = lat
        df.at[index, '경도'] = lng
        df.at[index, '지오코딩_상태'] = status
        df.at[index, '정제된_주소'] = clean_address_advanced(address)
        
        if lat is not None:
            success_count += 1
        
        # 진행상황 출력
        if (index + 1) % 100 == 0:
            current_success_rate = success_count / (index + 1) * 100
            print(f"진행률: {index + 1}/{len(df)} ({(index + 1)/len(df)*100:.1f}%) - 성공률: {current_success_rate:.1f}%")
        
        # API 호출 제한
        time.sleep(0.15)  # 조금 더 여유있게
    
    # 결과 저장
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # 최종 통계
    final_success_rate = success_count / len(df) * 100
    print(f"\n=== 최종 결과 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {len(df) - success_count}개")
    print(f"성공률: {final_success_rate:.1f}%")
    
    # 실패 원인 분석
    print("\n=== 실패 원인 분석 ===")
    failure_reasons = df[df['위도'].isna()]['지오코딩_상태'].value_counts()
    print(failure_reasons)
    
    return df

# 사용 예시
if __name__ == "__main__":
    API_KEY = "AB406882-BC3B-3852-B9BB-A10D73FB3A19"  # API 키 입력
    INPUT_FILE = "data/preprocessed/gangnam_restaurants_final.csv"
    OUTPUT_FILE = "data/preprocessed/gangnam_restaurants_with_coordinates.csv"
    ADDRESS_COLUMN = "주소"
    
    try:
        result_df = add_coordinates_robust(
            INPUT_FILE, 
            OUTPUT_FILE, 
            ADDRESS_COLUMN, 
            API_KEY
        )
        
        # 성공한 데이터 미리보기
        success_data = result_df[result_df['위도'].notna()]
        print(f"\n성공한 데이터 {len(success_data)}개 중 상위 5개:")
        print(success_data[['음식점_이름', '주소', '정제된_주소', '위도', '경도', '지오코딩_상태']].head())
        
    except Exception as e:
        print(f"오류 발생: {e}")
