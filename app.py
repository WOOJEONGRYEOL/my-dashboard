import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
from io import StringIO
import numpy as np
from scipy import stats

# 페이지 설정
st.set_page_config(
    page_title="종편 4사 주중 메인 시청률 대시보드",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="auto"  # 자동 감지
)

# 디바이스 감지 및 최적화 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    .main * {
        font-family: 'Noto Sans KR', sans-serif !important;
    }
    
    /* PC 최적화 */
    @media (min-width: 769px) {
        .main .block-container {
            padding-top: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        .stPlotlyChart {
            height: 500px !important;
        }
        .sidebar .block-container {
            padding-top: 2rem;
        }
    }
    
    /* 모바일 최적화 (768px 이하) */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem 0.5rem;
        }
        .stPlotlyChart {
            height: 350px !important;
        }
        .stSelectbox label, .stRadio label, .stMultiselect label {
            font-size: 14px !important;
        }
        .stButton button {
            width: 100%;
            font-size: 14px !important;
        }
        .stMetric {
            background-color: #f8f9fa;
            padding: 0.5rem;
            border-radius: 0.5rem;
            margin: 0.25rem 0;
        }
        .sidebar .block-container {
            padding: 1rem 0.5rem;
        }
        /* 모바일에서 차트 범례 위치 조정 */
        .js-plotly-plot .plotly .legend {
            font-size: 10px !important;
        }
    }
    
    /* 태블릿 최적화 (769px - 1024px) */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding: 1.5rem 1rem;
        }
        .stPlotlyChart {
            height: 450px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📺 종편 4사 주중 메인 시청률 대시보드")
st.markdown("---")

# 데이터 로딩 함수
@st.cache_data(ttl=300)
def load_data():
    try:
        url = "https://docs.google.com/spreadsheets/d/1uv9gNT9TDEu2qtPPOnQlhiznnb4lxmogwQFWmQbclIc/export?format=csv&gid=0"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv,application/csv,text/plain,*/*',
            'Accept-Charset': 'utf-8,euc-kr,cp949'
        }
        
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        # 인코딩 처리
        df = None
        encoding_used = None
        
        try:
            response_bytes = requests.get(url, timeout=10, headers=headers)
            response_bytes.raise_for_status()
            
            encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    text_content = response_bytes.content.decode(encoding)
                    df = pd.read_csv(StringIO(text_content))
                    
                    has_korean = any('뉴스' in str(col) or 'JTBC' in str(col) or 'MBN' in str(col) or 'TV조선' in str(col) for col in df.columns)
                    has_garbled = any('ë' in str(col) or 'ì' in str(col) or 'ì¡' in str(col) for col in df.columns)
                    
                    if has_korean or not has_garbled:
                        encoding_used = encoding
                        break
                        
                except (UnicodeDecodeError, pd.errors.EmptyDataError) as e:
                    continue
                    
        except Exception as e:
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            if response.encoding and response.encoding.lower() != 'utf-8':
                response.encoding = 'utf-8'
            df = pd.read_csv(StringIO(response.text))
            encoding_used = "fallback"
        
        # 한글 복구
        def fix_korean_columns(df):
            column_mapping = {
                'ë´ì¤A': '뉴스A',
                'JTBCë´ì¤ë£¸': 'JTBC뉴스룸', 
                'MBNë´ì¤7': 'MBN뉴스7',
                'TVì¡°ì ë´ì¤9': 'TV조선뉴스9',
                'ë´ì¤A(2049)': '뉴스A(2049)',
                'JTBCë´ì¤ë£¸(2049)': 'JTBC뉴스룸(2049)',
                'MBNë´ì¤7(2049)': 'MBN뉴스7(2049)', 
                'TVì¡°ì ë´ì¤9(2049)': 'TV조선뉴스9(2049)',
                'ë ì§': '날짜'
            }
            
            df = df.rename(columns=column_mapping)
            
            new_columns = []
            for col in df.columns:
                new_col = col
                replacements = {
                    'ë´ì¤': '뉴스', 'ë£¸': '룸', 'ì¡°ì ': '조선', 'ì§': '지',
                    'ì': '', 'ë': '', '¤': '', '¸': '', '£': ''
                }
                for old, new in replacements.items():
                    new_col = new_col.replace(old, new)
                new_columns.append(new_col)
            
            df.columns = new_columns
            return df
        
        df = fix_korean_columns(df)
        
        # 날짜 처리
        date_col = df.columns[0]
        df['original_date'] = df[date_col]
        
        try:
            df['date'] = pd.to_datetime(df[date_col].astype(str), format='%y%m%d', errors='coerce')
        except:
            df['date'] = pd.to_datetime(df[date_col], errors='coerce')
        
        if df['date'].isna().all():
            df['date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
        
        # 요일 추가
        df['weekday'] = df['date'].dt.dayofweek  # 0=월요일, 6=일요일
        df = df.sort_values('date').reset_index(drop=True)
        
        # 숫자 컬럼 처리
        numeric_columns = []
        exclude_columns = ['date', 'original_date', '날짜', 'Date', 'DATE', 'weekday']
        
        for col in df.columns:
            if col not in exclude_columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    if not df[col].isna().all():
                        numeric_columns.append(col)
                except:
                    pass
        
        loading_info = {
            'encoding': encoding_used,
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'date_column': date_col,
            'numeric_columns': numeric_columns,
            'date_range': (df['date'].min(), df['date'].max())
        }
        
        return df, numeric_columns, loading_info
        
    except Exception as e:
        error_info = {'error_type': 'processing', 'message': str(e)}
        return pd.DataFrame(), [], error_info

# 요일별 데이터 필터링 함수
def filter_by_day_type(df, day_type):
    if day_type == "주중":
        return df[df['weekday'].isin([0, 1, 2, 3, 4])]  # 월~금
    elif day_type == "주말":
        return df[df['weekday'].isin([5, 6])]  # 토,일
    else:  # "전체"
        return df

# 방송사별 색상
def get_channel_color(channel_name):
    if '뉴스A' in channel_name:
        return '#2563EB'  # 파랑
    elif 'JTBC' in channel_name:
        return '#9333EA'  # 보라
    elif 'MBN' in channel_name:
        return '#F97316'  # 주황
    elif 'TV조선' in channel_name or '조선' in channel_name:
        return '#DC2626'  # 빨강
    else:
        return '#10B981'

# 채널 딕셔너리 생성
def create_channels_dict(numeric_columns, show_2049=False):
    channels_dict = {}
    for col in numeric_columns:
        if show_2049 and '2049' in col:
            channels_dict[col] = {'color': get_channel_color(col), 'name': col}
        elif not show_2049 and '2049' not in col:
            channels_dict[col] = {'color': get_channel_color(col), 'name': col}
    return channels_dict

# 이동평균 차트
def create_moving_average_chart(df, channels, periods, CHANNELS):
    for channel in channels:
        if channel in df.columns:
            for period in periods:
                if len(df) >= period:
                    df[f"{channel}_MA{period}"] = df[channel].rolling(window=period, min_periods=1).mean()

    fig = go.Figure()
    
    for channel in channels:
        if channel in CHANNELS:
            for period in periods:
                col_name = f"{channel}_MA{period}"
                if col_name in df.columns and not df[col_name].isna().all():
                    
                    if period == 30:
                        line_style = dict(width=2)
                    elif period == 90:
                        line_style = dict(width=2.5, dash='dash')
                    else:
                        line_style = dict(width=3, dash='dot')
                    
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df[col_name],
                        mode='lines',
                        name=f'{CHANNELS[channel]["name"]} {period}일',
                        line=dict(color=CHANNELS[channel]["color"], **line_style),
                        hovertemplate=f'<b>{CHANNELS[channel]["name"]} ({period}일 MA)</b><br>' +
                                    '날짜: %{x|%Y년 %m월 %d일}<br>시청률: %{y:.2f}%<extra></extra>'
                    ))
    
    fig.update_layout(
        height=500,
        xaxis_title="날짜",
        yaxis_title="시청률 (%)",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(
            dtick="M1",  # 1달 간격
            tickformat="%y.%m",  # yy.mm 형식
            type="date",
            rangeslider=dict(visible=False)  # 스크롤바 완전 제거
        )
    )
    
    return fig

# 동기간 비교 차트 (기간 평균 방식)
def create_period_comparison_chart(df, channels, CHANNELS, comparison_type="최근 6개월", custom_dates=None):
    latest_date = df['date'].max()
    
    if custom_dates:
        start_date, end_date = custom_dates
        # 전년 동기간
        prev_start_date = start_date - pd.DateOffset(years=1)
        prev_end_date = end_date - pd.DateOffset(years=1)
        
        period_label = f"{start_date.strftime('%y.%m.%d')}~{end_date.strftime('%y.%m.%d')}"
        prev_period_label = f"{prev_start_date.strftime('%y.%m.%d')}~{prev_end_date.strftime('%y.%m.%d')}"
        title = f"선택기간 vs 전년 동기간 시청률 비교"
    else:
        # 개월 수 추출
        if "1개월" in comparison_type:
            months_count = 1
        elif "3개월" in comparison_type:
            months_count = 3
        elif "6개월" in comparison_type:
            months_count = 6
        elif "9개월" in comparison_type:
            months_count = 9
        else:  # "12개월"
            months_count = 12
        
        # 최근 N개월 기간 평균
        end_date = latest_date
        start_date = end_date - pd.DateOffset(months=months_count)
        
        # 전년 동기 평균
        prev_end_date = end_date - pd.DateOffset(years=1)
        prev_start_date = start_date - pd.DateOffset(years=1)
        
        # 라벨 생성 (yy.mm 형식)
        period_label = f"{start_date.strftime('%y.%m')}~{end_date.strftime('%y.%m')}"
        prev_period_label = f"{prev_start_date.strftime('%y.%m')}~{prev_end_date.strftime('%y.%m')}"
        title = f"{comparison_type} 평균 vs 전년 동기 평균 시청률 비교"
    
    # 현재 기간 데이터
    current_data = df[
        (df['date'] >= start_date) & (df['date'] <= end_date)
    ][channels].mean()
    
    # 전년 동기 데이터
    previous_data = df[
        (df['date'] >= prev_start_date) & (df['date'] <= prev_end_date)
    ][channels].mean()
    
    x_labels = [prev_period_label, period_label]
    
    fig = go.Figure()
    
    # 각 방송사별 막대
    for i, channel in enumerate(channels):
        if channel in CHANNELS:
            prev_val = previous_data.get(channel, 0)
            curr_val = current_data.get(channel, 0)
            
            # 증감 계산 (%p)
            diff = curr_val - prev_val
            diff_text = f"({diff:+.2f}%p)" if abs(diff) >= 0.01 else "(±0.00%p)"
            
            # 전년 막대
            fig.add_trace(go.Bar(
                name=f'{CHANNELS[channel]["name"]} (전년)',
                x=[x_labels[0]],
                y=[prev_val],
                marker_color=CHANNELS[channel]["color"],
                opacity=0.6,
                legendgroup=channel,
                offsetgroup=i,
                text=f'{prev_val:.2f}%',
                textposition='outside'
            ))
            
            # 현재 막대 (증감 표시를 위에 배치)
            fig.add_trace(go.Bar(
                name=f'{CHANNELS[channel]["name"]} (현재)',
                x=[x_labels[1]],
                y=[curr_val],
                marker_color=CHANNELS[channel]["color"],
                opacity=1.0,
                legendgroup=channel,
                offsetgroup=i,
                text=f'{curr_val:.2f}% <span style="color:{"red" if diff < 0 else "green"};">{diff_text}</span>',
                textposition='outside',
                textfont=dict(size=11)
            ))
    
    fig.update_layout(
        height=500,
        title=title,
        xaxis_title="기간",
        yaxis_title="시청률 (%)",
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# 산점도 차트
def create_scatter_chart(df, channels, CHANNELS):
    fig = go.Figure()
    
    for channel in channels:
        if channel in CHANNELS and channel in df.columns:
            # 산점도만 표시
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[channel],
                mode='markers',
                name=f'{CHANNELS[channel]["name"]}',
                marker=dict(
                    color=CHANNELS[channel]["color"],
                    size=6,
                    opacity=0.7
                ),
                hovertemplate=f'<b>{CHANNELS[channel]["name"]}</b><br>' +
                            '날짜: %{x}<br>시청률: %{y:.2f}%<extra></extra>'
            ))
    
    fig.update_layout(
        height=500,
        title="시청률 분포 산점도",
        xaxis_title="날짜",
        yaxis_title="시청률 (%)",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(
            dtick="M1",  # 1달 간격
            tickformat="%y.%m",  # yy.mm 형식
            type="date",
            rangeslider=dict(visible=False)  # 스크롤바 완전 제거
        )
    )
    
    return fig

# 요일별 시청률 막대그래프
def create_weekday_chart(df, channels, CHANNELS, period_type="전체"):
    # 기간별 데이터 필터링
    latest_date = df['date'].max()
    
    if period_type == "최근 1개월":
        start_date = latest_date - pd.DateOffset(months=1)
        filtered_df = df[df['date'] >= start_date]
    elif period_type == "최근 3개월":
        start_date = latest_date - pd.DateOffset(months=3)
        filtered_df = df[df['date'] >= start_date]
    elif period_type == "최근 6개월":
        start_date = latest_date - pd.DateOffset(months=6)
        filtered_df = df[df['date'] >= start_date]
    elif period_type == "최근 9개월":
        start_date = latest_date - pd.DateOffset(months=9)
        filtered_df = df[df['date'] >= start_date]
    elif period_type == "최근 12개월":
        start_date = latest_date - pd.DateOffset(months=12)
        filtered_df = df[df['date'] >= start_date]
    else:  # "전체"
        filtered_df = df
    
    # 요일별 시청률 계산
    df_weekday = filtered_df.copy()
    df_weekday['weekday_name'] = df_weekday['date'].dt.day_name()
    
    # 요일 순서 설정 (월~금)
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    weekday_korean = ['월요일', '화요일', '수요일', '목요일', '금요일']
    
    fig = go.Figure()
    
    # 각 방송사별 막대 추가
    for channel in channels:
        if channel in CHANNELS and channel in df_weekday.columns:
            weekday_avg = df_weekday.groupby('weekday_name')[channel].mean()
            
            # 요일 순서로 정렬
            y_values = []
            for day in weekday_order:
                if day in weekday_avg.index:
                    y_values.append(weekday_avg[day])
                else:
                    y_values.append(0)
            
            fig.add_trace(go.Bar(
                x=weekday_korean,
                y=y_values,
                name=CHANNELS[channel]['name'],
                marker_color=CHANNELS[channel]['color'],
                text=[f'{val:.2f}%' for val in y_values],
                textposition='outside'
            ))
    
    fig.update_layout(
        height=500,
        title=f"요일별 평균 시청률 ({period_type})",
        xaxis_title="요일",
        yaxis_title="시청률 (%)",
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# 스테이션별 상관관계
def create_correlation_analysis(df, channels, analysis_period):
    # 분석 기간에 따른 데이터 필터링
    if analysis_period != "전체":
        recent_data = df.tail(analysis_period)
    else:
        recent_data = df
    
    # 상관관계 계산
    corr_matrix = recent_data[channels].corr()
    
    # 히트맵
    fig = px.imshow(
        corr_matrix,
        x=channels,
        y=channels,
        color_continuous_scale='RdBu',
        aspect='auto',
        title=f"스테이션별 시청률 상관관계 ({analysis_period}일 기준)" if analysis_period != "전체" else "스테이션별 시청률 상관관계 (전체 기간)"
    )
    
    # 상관계수 텍스트 추가
    for i in range(len(channels)):
        for j in range(len(channels)):
            fig.add_annotation(
                x=j, y=i,
                text=f"{corr_matrix.iloc[i, j]:.2f}",
                showarrow=False,
                font=dict(color="white" if abs(corr_matrix.iloc[i, j]) > 0.5 else "black")
            )
    
    fig.update_layout(height=400)
    
    # 모든 상관관계 수치를 담은 데이터프레임 생성
    corr_pairs = []
    for i in range(len(channels)):
        for j in range(i+1, len(channels)):
            corr_pairs.append({
                '방송사 1': channels[i],
                '방송사 2': channels[j],
                '상관계수': round(corr_matrix.iloc[i, j], 3)
            })
    
    corr_df = pd.DataFrame(corr_pairs).sort_values('상관계수', key=abs, ascending=False)
    
    return fig, corr_df

# 사이드바
with st.sidebar:
    st.header("🎛️ 분석 옵션")
    
    if st.button("🔄 데이터 새로고침", type="primary"):
        st.cache_data.clear()
        st.rerun()

# 데이터 로드
with st.spinner("📊 구글 시트에서 데이터 로딩 중..."):
    result = load_data()
    
    if len(result) == 3:
        df, numeric_columns, loading_info = result
    else:
        df, numeric_columns = result[:2]
        loading_info = None

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
    st.stop()

# 사이드바 컨트롤
with st.sidebar:
    st.markdown("---")
    
    # 요일 선택 추가
    st.subheader("📅 요일 선택")
    day_type = st.radio(
        "분석할 요일을 선택하세요:",
        ["주중", "주말", "전체(주중+주말)"],
        index=0,
        help="주중: 월~금, 주말: 토~일"
    )
    
    # 선택한 요일에 따라 데이터 필터링
    filtered_df = filter_by_day_type(df, day_type)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 시청률 유형 선택
    st.subheader("📊 시청률 유형")
    rating_type = st.radio(
        "표시할 시청률을 선택하세요:",
        ["수도권 유료가구 시청률", "2049 시청률"],
        index=0,
        help="둘 중 하나만 선택 가능"
    )
    
    show_2049 = rating_type == "2049 시청률"
    CHANNELS = create_channels_dict(numeric_columns, show_2049)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 차트 유형 선택
    st.subheader("📈 차트 유형")
    chart_type = st.radio(
        "분석 방법을 선택하세요:",
        ["이동평균선", "동기간 비교", "시청률 분포 산점도", "요일별 시청률 비교", "스테이션별 상관관계"],
        index=0
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 차트별 옵션
    if chart_type == "이동평균선":
        st.subheader("📈 이동평균 기간")
        
        # 뉴스A가 있으면 기본 선택, 없으면 첫 번째 채널
        default_channel = None
        for channel in CHANNELS.keys():
            if '뉴스A' in channel:
                default_channel = channel
                break
        if not default_channel and CHANNELS:
            default_channel = list(CHANNELS.keys())[0]
        
        # 기본값을 30, 90, 180으로 설정
        periods = st.multiselect(
            "기간을 선택하세요:",
            [30, 90, 180],
            default=[30, 90, 180],
            help="여러 개 선택 가능"
        )
        
    elif chart_type == "동기간 비교":
        st.subheader("📊 비교 기간")
        
        # 날짜 범위 직접 선택 옵션 먼저 확인
        use_custom_dates = st.checkbox("기간 직접 선택")
        
        comparison_type = None
        custom_dates = None
        
        if use_custom_dates:
            # 직접 선택 모드
            st.markdown("**직접 기간 선택:**")
            min_date = loading_info['date_range'][0].date()
            max_date = loading_info['date_range'][1].date()
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "시작일",
                    value=max_date - timedelta(days=90),
                    min_value=min_date,
                    max_value=max_date
                )
            with col2:
                end_date = st.date_input(
                    "종료일",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )
            
            # 선택한 날짜가 데이터 범위를 벗어나는지 확인
            if start_date < min_date or end_date > max_date or start_date > end_date:
                st.error("❌ 보유하지 않은 데이터 범위입니다.")
                custom_dates = None
            else:
                custom_dates = (pd.Timestamp(start_date), pd.Timestamp(end_date))
        else:
            # 기본 선택 모드
            comparison_type = st.radio(
                "비교 기간:",
                ["최근 1개월", "최근 3개월", "최근 6개월", "최근 9개월", "최근 12개월"],
                index=2,
                help="전년 동기와 비교할 기간을 선택하세요 (해당 기간 평균)"
            )
        
    elif chart_type == "시청률 분포 산점도":
        st.subheader("📊 산점도 옵션")
        st.markdown("각 방송사의 일별 시청률을 점으로 표시합니다.")
        
    elif chart_type == "요일별 시청률 비교":
        st.subheader("📊 비교 옵션")
        period_type = st.selectbox(
            "분석 기간:",
            ["전체", "최근 1개월", "최근 3개월", "최근 6개월", "최근 9개월", "최근 12개월"],
            index=2,
            help="선택한 기간의 요일별 평균 시청률을 표시합니다"
        )
        
    elif chart_type == "스테이션별 상관관계":
        st.subheader("📊 분석 옵션")
        analysis_period = st.selectbox(
            "분석 기간:",
            ["전체", 30, 90, 180],
            index=0
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 방송사 선택 (모든 차트 유형에서 가능)
    st.subheader("📺 방송사 선택")
    
    # 이동평균선에서는 뉴스A를 기본 선택
    if chart_type == "이동평균선" and default_channel:
        default_channels = [default_channel]
    else:
        default_channels = list(CHANNELS.keys())
    
    channels = st.multiselect(
        "방송사를 선택하세요:",
        list(CHANNELS.keys()),
        default=default_channels,
        help="여러 개 선택 가능"
    )
    
    # 데이터 정보
    st.markdown("---")
    st.subheader("📋 데이터 정보")
    st.write(f"**총 데이터**: {len(filtered_df)}행 (필터링 후)")
    if not filtered_df.empty and 'date' in filtered_df.columns:
        st.write(f"**기간**: {filtered_df['date'].min().strftime('%Y-%m-%d')} ~ {filtered_df['date'].max().strftime('%Y-%m-%d')}")
    st.write(f"**현재 표시**: {rating_type}")
    st.write(f"**요일 필터**: {day_type}")
    st.write(f"**차트 유형**: {chart_type}")

# 메인 차트
if channels and not filtered_df.empty:
    if chart_type == "이동평균선" and periods:
        st.subheader(f"📈 {rating_type} 이동평균선 ({day_type})")
        fig = create_moving_average_chart(filtered_df, channels, periods, CHANNELS)
        st.plotly_chart(fig, use_container_width=True)
        
        # 차트 조작 가이드
        with st.expander("📖 차트 조작 가이드"):
            total_days = (filtered_df['date'].max() - filtered_df['date'].min()).days
            if total_days > 540:
                st.markdown("**📊 하단 화이트 스크롤바:**")
                st.markdown("- 스크롤바를 **좌우로 드래그**하여 과거 데이터 탐색")
                st.markdown("- 초기 화면: 최근 1년 반 데이터 표시")
            else:
                st.markdown("**📊 전체 데이터 표시 중**")
                st.markdown("- 데이터가 1년 반 이하로 전체 기간을 한 번에 표시합니다")
        
        # 현재 수치 표시 (이동평균선일 때만)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 선택기간 평균 시청률")
            
            if not filtered_df.empty:
                latest_date = filtered_df['date'].max()
                st.info(f"**기준일**: {latest_date.strftime('%Y년 %m월 %d일')}")
                
                cols = st.columns(min(len(channels), 4))
                for i, channel in enumerate(channels[:4]):
                    with cols[i]:
                        st.markdown(f"**{CHANNELS[channel]['name']}**")
                        for period in periods:
                            col_name = f"{channel}_MA{period}"
                            if col_name in filtered_df.columns and not filtered_df[col_name].empty:
                                latest = filtered_df[col_name].iloc[-1]
                                if not pd.isna(latest):
                                    st.metric(f"{period}일", f"{latest:.2f}%")
        
        with col2:
            st.subheader("🎨 범례")
            
            st.markdown("**방송사별 색상:**")
            for channel, info in CHANNELS.items():
                if channel in channels:
                    st.markdown(
                        f'<span style="color: {info["color"]}; font-weight: bold;">● {info["name"]}</span>',
                        unsafe_allow_html=True
                    )
            
            st.markdown("**선 스타일:**")
            st.markdown("- **실선**: 30일 이동평균")
            st.markdown("- **대시선**: 90일 이동평균")
            st.markdown("- **점선**: 180일 이동평균")
        
    elif chart_type == "동기간 비교":
        st.subheader(f"📊 {rating_type} 동기간 비교 ({day_type})")
        if use_custom_dates and custom_dates:
            fig = create_period_comparison_chart(filtered_df, channels, CHANNELS, custom_dates=custom_dates)
        elif comparison_type:
            fig = create_period_comparison_chart(filtered_df, channels, CHANNELS, comparison_type)
        else:
            st.warning("비교 기간을 선택해주세요.")
            fig = None
            
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "시청률 분포 산점도":
        st.subheader(f"🔸 {rating_type} 시청률 분포 산점도 ({day_type})")
        fig = create_scatter_chart(filtered_df, channels, CHANNELS)
        st.plotly_chart(fig, use_container_width=True)
        
        # 차트 조작 가이드
        with st.expander("📖 차트 조작 가이드"):
            st.markdown("**📊 하단 범위 슬라이더:**")
            st.markdown("- 슬라이더 양 끝을 **드래그**하여 표시 범위 조정")
            st.markdown("- 슬라이더 중앙 부분을 **드래그**하여 좌우 이동")
            st.markdown("- 더블클릭으로 전체 범위 표시")
        
    elif chart_type == "요일별 시청률 비교":
        st.subheader(f"📊 {rating_type} 요일별 시청률 비교")
        if channels:
            # 주중/주말 필터링이 적용된 상태에서는 요일별 분석이 제한적일 수 있음을 알림
            if day_type != "전체(주중+주말)":
                st.info(f"현재 {day_type} 데이터만 분석 중입니다. 전체 요일 패턴을 보려면 '전체(주중+주말)'을 선택하세요.")
            
            # 원본 데이터를 사용 (요일별 분석은 전체 데이터 기준)
            fig = create_weekday_chart(df, channels, CHANNELS, period_type)
            st.plotly_chart(fig, use_container_width=True)
            
            # 요일별 패턴 분석
            st.markdown("### 📋 요일별 패턴 분석")
            
            # 기간별 데이터 필터링 (위의 함수와 동일한 로직)
            latest_date = df['date'].max()
            
            if period_type == "최근 1개월":
                start_date = latest_date - pd.DateOffset(months=1)
                analysis_df = df[df['date'] >= start_date]
            elif period_type == "최근 3개월":
                start_date = latest_date - pd.DateOffset(months=3)
                analysis_df = df[df['date'] >= start_date]
            elif period_type == "최근 6개월":
                start_date = latest_date - pd.DateOffset(months=6)
                analysis_df = df[df['date'] >= start_date]
            elif period_type == "최근 9개월":
                start_date = latest_date - pd.DateOffset(months=9)
                analysis_df = df[df['date'] >= start_date]
            elif period_type == "최근 12개월":
                start_date = latest_date - pd.DateOffset(months=12)
                analysis_df = df[df['date'] >= start_date]
            else:  # "전체"
                analysis_df = df
            
            # 요일별 평균 계산
            analysis_df = analysis_df.copy()
            analysis_df['weekday_name'] = analysis_df['date'].dt.day_name()
            
            # 요일 순서 설정
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            weekday_korean = ['월요일', '화요일', '수요일', '목요일', '금요일']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**📊 {period_type} 요일별 평균 시청률**")
                
                # 전체 방송사 평균 계산
                all_channels_avg = {}
                for day_eng, day_kor in zip(weekday_order, weekday_korean):
                    day_data = analysis_df[analysis_df['weekday_name'] == day_eng]
                    if len(day_data) > 0:
                        # 선택된 채널들의 평균
                        day_avg = day_data[channels].mean().mean()
                        all_channels_avg[day_kor] = day_avg
                
                if all_channels_avg:
                    max_day = max(all_channels_avg, key=all_channels_avg.get)
                    min_day = min(all_channels_avg, key=all_channels_avg.get)
                    
                    for day_kor in weekday_korean:
                        if day_kor in all_channels_avg:
                            avg_val = all_channels_avg[day_kor]
                            if day_kor == max_day:
                                st.success(f"{day_kor}: {avg_val:.2f}% 🏆 (최고)")
                            elif day_kor == min_day:
                                st.error(f"{day_kor}: {avg_val:.2f}% 📉 (최저)")
                            else:
                                st.info(f"{day_kor}: {avg_val:.2f}%")
            
            with col2:
                st.markdown("**💡 패턴 해석**")
                
                if all_channels_avg:
                    st.markdown(f"- **최고 시청률**: {max_day}")
                    st.markdown(f"- **최저 시청률**: {min_day}")
                    
                    # 변동성 계산
                    avg_values = list(all_channels_avg.values())
                    variation = ((max(avg_values) - min(avg_values)) / np.mean(avg_values)) * 100
                    
                    if variation > 20:
                        st.markdown(f"- **변동성**: 높음 ({variation:.1f}%)")
                    elif variation > 10:
                        st.markdown(f"- **변동성**: 보통 ({variation:.1f}%)")
                    else:
                        st.markdown(f"- **변동성**: 낮음 ({variation:.1f}%)")
                    
                    st.markdown(f"- **분석 기간**: {period_type}")
                    if period_type != "전체":
                        st.markdown(f"- **데이터 기간**: {start_date.strftime('%Y.%m.%d')} ~ {latest_date.strftime('%Y.%m.%d')}")
        else:
            st.warning("방송사를 선택해주세요.")
        
    elif chart_type == "스테이션별 상관관계":
        st.subheader(f"🌈 {rating_type} 스테이션별 상관관계 ({day_type})")
        if len(channels) >= 2:
            fig, corr_df = create_correlation_analysis(filtered_df, channels, analysis_period)
            st.plotly_chart(fig, use_container_width=True)
            
            # 상관관계 해석
            st.markdown("### 📋 스테이션별 상관관계 수치")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**📊 모든 방송사 간 상관관계**")
                
                # 상관관계 강도별 색상 표시
                def get_correlation_color(corr_val):
                    abs_corr = abs(corr_val)
                    if abs_corr >= 0.7:
                        return "🟢"  # 매우 강함
                    elif abs_corr >= 0.5:
                        return "🟡"  # 강함
                    elif abs_corr >= 0.3:
                        return "🟠"  # 보통
                    else:
                        return "🔴"  # 약함
                
                for _, row in corr_df.iterrows():
                    color_indicator = get_correlation_color(row['상관계수'])
                    st.markdown(f"{color_indicator} **{row['방송사 1']}** ↔ **{row['방송사 2']}**: {row['상관계수']}")
                        
            with col2:
                st.markdown("**📊 상관관계 강도 기준**")
                st.markdown("🟢 0.7 이상: 매우 강한 연관성")
                st.markdown("🟡 0.5~0.7: 강한 연관성") 
                st.markdown("🟠 0.3~0.5: 보통 연관성")
                st.markdown("🔴 0.3 미만: 약한 연관성")
                
                st.markdown("**💡 해석 가이드**")
                st.markdown("- 양수: 같은 방향으로 변화")
                st.markdown("- 음수: 반대 방향으로 변화")
                st.markdown("- 절댓값이 클수록 연관성 강함")
        else:
            st.warning("상관관계 분석을 위해 최소 2개 방송사를 선택해주세요.")

else:
    if filtered_df.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    elif not channels:
        st.warning("방송사를 선택해주세요.")
    elif chart_type == "이동평균선" and not periods:
        st.warning("분석 기간을 선택해주세요.")

# 원본 데이터 미리보기
if not df.empty:
    with st.expander("🔍 원본 데이터 미리보기"):
        st.dataframe(df.head(10), use_container_width=True)

# 하단 로딩 정보
if loading_info and 'encoding' in loading_info:
    st.markdown("---")
    with st.expander("🔧 데이터 로딩 정보"):
        st.success(f"🔗 구글 시트 접속 완료")
        st.success(f"✅ 인코딩 성공: {loading_info['encoding']}")
        st.success(f"✅ 데이터 로드 완료! ({loading_info['rows']}행, {loading_info['columns']}열)")
        st.info(f"📋 복구된 컬럼들: {loading_info['column_names']}")
        st.write(f"📅 날짜 컬럼으로 사용: `{loading_info['date_column']}`")
        st.write(f"📊 숫자 데이터 컬럼들: {loading_info['numeric_columns']}")
        if 'date_range' in loading_info:
            st.write(f"📆 데이터 범위: {loading_info['date_range'][0].strftime('%Y-%m-%d')} ~ {loading_info['date_range'][1].strftime('%Y-%m-%d')}")