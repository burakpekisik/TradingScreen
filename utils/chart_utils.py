import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from helpers.heikinashi import heikin_ashi


def find_nearest_bar(timestamp, data_index):
    """En yakın bar zamanını bul"""
    return data_index[abs(data_index - timestamp).argmin()]


def calculate_ma(data, period, ma_type="SMA"):
    """Calculate Moving Average"""
    if ma_type == "EMA":
        return data["close"].ewm(span=period, adjust=False).mean()
    return data["close"].rolling(window=period).mean()


def create_candlestick_chart(
    data,
    symbol,
    timeframe,
    cutoff_index=None,
    trades=None,
    indicator_signals=None,
    moving_averages=None,
    chart_type="normal",
):
    """Create Plotly candlestick chart with TradingView-like controls"""
    time_formats = {
        "1m": "%H:%M",
        "5m": "%H:%M",
        "15m": "%H:%M",
        "30m": "%H:%M",
        "1h": "%H:%M",
        "4h": "%d.%m.%Y %H:%M",
        "1d": "%d.%m.%Y",
        "1w": "%d.%m.%Y",
        "1M": "%d.%m.%Y",
    }

    display_data = data.iloc[:cutoff_index] if cutoff_index is not None else data

    # Convert to Heikin-Ashi if selected
    if chart_type == "heikinashi":
        display_data = heikin_ashi(display_data)

    # Tarihleri kısa formata çevirmek için
    display_data['date'] = pd.to_datetime(display_data.index).strftime('%Y-%m-%dT%H:%M:%S')

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=display_data['date'],  # Artık kısa formatta tarihler
                open=display_data["open"],
                high=display_data["high"],
                low=display_data["low"],
                close=display_data["close"],
                name="Heikin-Ashi" if chart_type == "heikinashi" else "Candlesticks",
            )
        ]
    )

    fig.update_layout(
        title=f"{symbol} {timeframe} Chart",
        yaxis_title="Price",
        xaxis_title="Date",
        template="plotly_dark",
        height=800,
        dragmode="pan",
        xaxis={
            "type": "category",
            "tickformat": time_formats.get(timeframe, "%d.%m.%Y"),
            "rangebreaks": [
                dict(bounds=["sat", "mon"]),
                dict(bounds=[16, 9.5], pattern="hour"),
            ],
            "tickmode": "auto",
            "nticks": 10,
            "hoverformat": "%d.%m.%Y %H:%M",
            "rangeslider": {"visible": False},
            "showspikes": True,
            "spikemode": "across",
            "spikesnap": "cursor",
            "tickformatstops": [
                dict(dtickrange=[None, 1000], value="%H:%M"),
                dict(dtickrange=[1000, 60000], value="%H:%M"),
                dict(dtickrange=[60000, 3600000], value="%H:%M"),
                dict(dtickrange=[3600000, 86400000], value="%d.%m.%Y %H:%M"),
                dict(dtickrange=[86400000, None], value="%d.%m.%Y"),
            ],
        },
        yaxis={
            "showspikes": True,  # Show horizontal line on hover
            "spikemode": "across",
            "spikesnap": "cursor",
            "fixedrange": False,  # Allow y-axis zooming
        },
        modebar_remove=[
            "autoScale2d",
            "lasso2d",
            "select2d",
        ],
        modebar_add=[
            "drawopenpath",
            "eraseshape",
            "zoomIn2d",
            "zoomOut2d",
        ],
        showlegend=False,
        # Add mouse wheel zoom and other interactions
        hovermode="x unified",
    )

    # Alternatif olarak, mevcut grafikte x ekseni formatını değiştirmek için
    fig.update_xaxes(
        tickformat='%Y-%m-%dT%H:%M:%S'
    )

    # Add reset button to modebar
    fig.update_layout(
        {
            "modebar": {
                "orientation": "v",
                "bgcolor": "rgba(0,0,0,0)",
                "color": "white",
                "activecolor": "#9ED3CD",
            }
        }
    )

    if trades:
        for trade in trades:
            # İşlem zamanını en yakın bara eşleştir
            nearest_timestamp = find_nearest_bar(trade["timestamp"], display_data.index)

            fig.add_trace(
                go.Scatter(
                    x=[nearest_timestamp],
                    y=[trade["price"]],
                    mode="markers",
                    marker=dict(
                        symbol=(
                            "triangle-up" if trade["type"] == "BUY" else "triangle-down"
                        ),
                        size=15,
                        color="green" if trade["type"] == "BUY" else "red",
                    ),
                    name=trade["type"],
                    showlegend=False,
                )
            )

    # Add indicator signals if available
    if indicator_signals is not None:
        for signal in indicator_signals:
            # İndikatör sinyallerini de en yakın bara eşleştir
            nearest_timestamp = find_nearest_bar(
                signal["timestamp"], display_data.index
            )

            fig.add_trace(
                go.Scatter(
                    x=[nearest_timestamp],
                    y=[signal["price"]],
                    mode="markers",
                    marker=dict(
                        symbol=(
                            "triangle-up" if signal["type"] == "AL" else "triangle-down"
                        ),
                        size=15,
                        color=(
                            "#00FFFF" if signal["type"] == "AL" else "#FF69B4"
                        ),  # Cyan for buy, Hot Pink for sell
                        line=dict(color="white", width=1),  # Beyaz kenar çizgisi
                    ),
                    name=f"{signal['indicator']} {signal['type']}",
                    showlegend=True,
                )
            )

    # Add moving averages if available
    if moving_averages:
        for ma in moving_averages:
            ma_data = calculate_ma(data, ma["period"], ma["type"])
            display_ma = (
                ma_data.iloc[:cutoff_index] if cutoff_index is not None else ma_data
            )
            
            # Tarihleri kısa formata çevir
            ma_dates = pd.to_datetime(display_data.index).strftime('%Y-%m-%dT%H:%M:%S')

            fig.add_trace(
                go.Scatter(
                    x=ma_dates,  # Kısa formatlı tarihleri kullan
                    y=display_ma,
                    mode="lines",
                    name=f"{ma['type']}-{ma['period']}",
                    line=dict(width=1, color=ma["color"]),
                    showlegend=True,
                )
            )

    return fig


def display_statistics(data):
    """Display market statistics"""
    st.subheader("Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"{data['close'].iloc[-1]:.2f}")
    col2.metric(
        "Daily Change",
        f"{((data['close'].iloc[-1] - data['open'].iloc[-1]) / data['open'].iloc[-1] * 100):.2f}%",
    )
    col3.metric("Volume", f"{data['volume'].iloc[-1]:,.0f}")
