import pandas as pd
import argparse
import os
import sys

def process_restaurant_data(input_file, output_file):
    """
    음식점 데이터를 처리하는 함수
    
    Args:
        input_file (str): 입력 CSV 파일 경로
        output_file (str): 출력 CSV 파일 경로
    """
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    
    # 1. 데이터 로드
    try:
        df = pd.read_csv(input_file, encoding='utf-8', header=0, on_bad_lines='skip', low_memory=False)
    except FileNotFoundError:
        print(f"오류: 입력 파일 '{input_file}'을 찾을 수 없습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {e}")
        sys.exit(1)
    
    # 원본 데이터 수 저장
    original_count = len(df)
    print(f"원본 총 데이터 수: {original_count}")
    
    # 2. 영업 중인 식당만 필터링
    df = df[df['상세영업상태명'] == '영업']
    business_count = len(df)
    print(f"영업 중인 식당 수: {business_count}")
    
    # 3. 결측치 처리: 결측치 비율이 50% 이상인 컬럼 삭제
    # null_ratio = df.isnull().mean()
    # df = df.loc[:, null_ratio < 0.5]
    
    # 4. 필요한 컬럼만 선택하여 정제
    df_cleaned = df[['관리번호', '인허가일자', '소재지면적', '사업장명']]
    df_cleaned.columns = ['음식점ID', '인허가일자', '소재지면적', '음식점명']
    
    # 5. '(한시적)'이 포함된 음식점 제외 및 '(주)' 제거
    df_filtered = df_cleaned[~df_cleaned['음식점명'].str.contains('(한시적)', regex=False, na=False)].copy()
    df_filtered['음식점명'] = df_filtered['음식점명'].str.replace('(주)', '', regex=False).str.strip()
    
    # 6. 결과 확인 및 저장
    print(f"컬럼 선택 후 데이터 행 수: {len(df_cleaned)}")
    print(f"전체 제거된 행 수: {original_count - len(df_filtered)}")
    
    # 7. 최종 데이터 저장
    try:
        # 출력 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df_filtered.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"처리된 데이터가 '{output_file}'에 저장되었습니다.")
    except Exception as e:
        print(f"데이터 저장 중 오류 발생: {e}")
        sys.exit(1)
    
    return df_filtered


def main():
    # 스크립트 위치 기준 상대 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(script_dir, '..', '..', 'data', 'raw', '서울시 관악구 일반음식점 인허가 정보.csv')
    default_output = os.path.join(script_dir, '..', '..', 'data', 'interim', 'gwanak_restaurants_cleaned.csv')
    
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description='음식점 데이터 처리 스크립트')
    parser.add_argument('--input', '-i', type=str, default=default_input,
                        help='입력 CSV 파일 경로 (기본값: %(default)s)')
    parser.add_argument('--output', '-o', type=str, default=default_output,
                        help='출력 CSV 파일 경로 (기본값: %(default)s)')
    
    args = parser.parse_args()
    
    # 데이터 처리 실행
    process_restaurant_data(args.input, args.output)

if __name__ == '__main__':
    main()
