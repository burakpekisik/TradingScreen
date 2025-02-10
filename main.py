import streamlit as st
from utils.market_data import fetch_market_symbols, fetch_market_data, get_full_symbol
from utils.intervals import get_interval
from utils.chart_utils import create_candlestick_chart, display_statistics
from utils.config import MARKETS, TIMEFRAMES, EXCHANGE_MAPPINGS
import random
import sqlite3
import pandas as pd
from utils.db_utils import (
    init_db,
    get_user_balance,
    update_user_balance,
    add_transaction,
    update_asset,
    init_user,
)
from datetime import datetime
from helpers.indicator_info import indicators

st.set_page_config(page_title="Market Data Viewer", layout="wide")


def initialize_session_state():
    if "symbols" not in st.session_state:
        market = MARKETS[0]  # Varsayılan market
        st.session_state.symbols = fetch_market_symbols(
            market
        )  # Sembolleri hemen yükle
    if "selected_market" not in st.session_state:
        st.session_state.selected_market = MARKETS[0]
    if "selected_symbol" not in st.session_state:
        st.session_state.selected_symbol = None
    if "cutoff_index" not in st.session_state:
        st.session_state.cutoff_index = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = 1  # Demo user
    if "trades" not in st.session_state:
        st.session_state.trades = []
    if "show_buy_input" not in st.session_state:
        st.session_state.show_buy_input = False
    if "show_sell_input" not in st.session_state:
        st.session_state.show_sell_input = False
    if "chart_key" not in st.session_state:
        st.session_state.chart_key = "main_chart"
    if "trade_action" not in st.session_state:
        st.session_state.trade_action = None
    if "last_update" not in st.session_state:
        st.session_state.last_update = datetime.now()
    if "chart_layout" not in st.session_state:
        st.session_state.chart_layout = None
    if "chart_config" not in st.session_state:
        st.session_state.chart_config = None
    if "active_indicator" not in st.session_state:
        st.session_state.active_indicator = None
    if "indicator_signals" not in st.session_state:
        st.session_state.indicator_signals = []
    if "moving_averages" not in st.session_state:
        st.session_state.moving_averages = []
    if "ma_counter" not in st.session_state:
        st.session_state.ma_counter = 0
    if "chart_type" not in st.session_state:
        st.session_state.chart_type = "normal"
    if "last_symbol" not in st.session_state:
        st.session_state.last_symbol = None


def update_symbols(market):
    if market != st.session_state.selected_market:
        st.session_state.symbols = fetch_market_symbols(market)
        st.session_state.selected_market = market
        if st.session_state.symbols:
            st.session_state.selected_symbol = st.session_state.symbols[0]


def update_chart(
    data, selected_symbol, timeframe, cutoff_index=None, container=None, key=None
):
    if container:
        with container:
            # Trades listesini cutoff_index'e göre filtrele
            filtered_trades = st.session_state.trades
            filtered_signals = st.session_state.indicator_signals

            if cutoff_index is not None:
                current_timestamp = data.index[cutoff_index - 1]
                filtered_trades = [
                    trade
                    for trade in st.session_state.trades
                    if trade["timestamp"] <= current_timestamp
                ]
                filtered_signals = [
                    signal
                    for signal in st.session_state.indicator_signals
                    if signal["timestamp"] <= current_timestamp
                ]

            fig = create_candlestick_chart(
                data,
                selected_symbol,
                timeframe,
                cutoff_index,
                trades=filtered_trades,
                indicator_signals=filtered_signals,
                moving_averages=st.session_state.moving_averages,
                chart_type=st.session_state.chart_type,
            )

            # Restore previous layout if exists
            if st.session_state.chart_layout:
                fig.update_layout(
                    xaxis_range=st.session_state.chart_layout.get("xaxis.range", None),
                    yaxis_range=st.session_state.chart_layout.get("yaxis.range", None),
                )

            # Save current layout before displaying
            def handle_layout_change(fig, layout, config):
                st.session_state.chart_layout = layout
                st.session_state.chart_config = config

            st.plotly_chart(
                fig,
                use_container_width=True,
                key=key if key else "default_chart",
                on_change=handle_layout_change,
            )


def main():
    st.title("Market Data Viewer")
    st.sidebar.header("Settings")

    initialize_session_state()

    # Add containers
    chart_container = st.empty()
    trading_container = st.container()
    portfolio_container = st.container()

    # Market selection
    market = st.sidebar.selectbox("Select Market", MARKETS, key="market")

    # Chart type selection in sidebar (add this before timeframe selection)
    chart_type = st.sidebar.radio(
        "Chart Type", ["Normal", "Heikin-Ashi"], key="chart_type_radio"
    )
    st.session_state.chart_type = chart_type.lower().replace("-", "")

    timeframe = st.sidebar.selectbox("Select Timeframe", TIMEFRAMES)

    # Yeni "Random Symbol" butonu
    if st.sidebar.button("Random Symbol"):
        if st.session_state.symbols:
            # Mevcut sembolü kaydet
            st.session_state.last_symbol = st.session_state.selected_symbol
            
            # Şu anki sembol dışındaki sembollerden rastgele seç
            available_symbols = [s for s in st.session_state.symbols if s != st.session_state.selected_symbol]
            if available_symbols:
                random_symbol = random.choice(available_symbols)
                st.session_state.selected_symbol = random_symbol
                
                # Yeni sembol için veri çek
                try:
                    with st.spinner("Fetching data for new symbol..."):
                        exchange = EXCHANGE_MAPPINGS.get(market)
                        interval = get_interval(timeframe)
                        full_symbol = get_full_symbol(market, random_symbol)
                        
                        data = fetch_market_data(full_symbol, exchange, interval)
                        
                        if data is not None and not data.empty:
                            st.session_state.current_data = data
                            
                            # Rastgele bir nokta seç
                            min_idx = int(len(data) * 0.2)
                            max_idx = int(len(data) * 0.8)
                            st.session_state.cutoff_index = random.randint(min_idx, max_idx)
                            
                            # Aktif indikatör varsa sinyalleri hesapla
                            if st.session_state.active_indicator and st.session_state.active_indicator != "None":
                                indicator_func = indicators[st.session_state.active_indicator]
                                signals_df = indicator_func(data, random_symbol, timeframe)
                                
                                st.session_state.indicator_signals = [
                                    {
                                        "timestamp": pd.to_datetime(row["Sinyal Tarihi"], format="%d.%m.%Y %H:%M"),
                                        "price": row["Son Fiyat"],
                                        "type": row["Sinyal Türü"],
                                        "indicator": st.session_state.active_indicator,
                                    }
                                    for _, row in signals_df.iterrows()
                                ]
                            
                            st.rerun()
                except Exception as e:
                    st.error(f"Error fetching data: {str(e)}")
                    # Hata durumunda önceki sembole geri dön
                    st.session_state.selected_symbol = st.session_state.last_symbol

    # Sayfa ilk yüklendiğinde veya market değiştiğinde sembolleri yükle
    if not st.session_state.symbols or market != st.session_state.selected_market:
        with st.spinner(f"Loading {market} symbols..."):
            st.session_state.symbols = fetch_market_symbols(market)
            st.session_state.selected_market = market
            if st.session_state.symbols:
                st.session_state.selected_symbol = st.session_state.symbols[0]

    # Symbol selection
    if st.session_state.symbols:
        selected_symbol = st.sidebar.selectbox(
            "Select Symbol",
            st.session_state.symbols,
            key="symbol",
            index=(
                st.session_state.symbols.index(st.session_state.selected_symbol)
                if st.session_state.selected_symbol in st.session_state.symbols
                else 0
            ),
        )
        st.session_state.selected_symbol = selected_symbol
    else:
        st.sidebar.error(f"No symbols available for {market}")

    # Indicator selection
    indicator_name = st.sidebar.selectbox(
        "Select Indicator", ["None"] + list(indicators.keys()), key="indicator"
    )

    if indicator_name != "None" and indicator_name != st.session_state.active_indicator:
        st.session_state.active_indicator = indicator_name
        if "current_data" in st.session_state:
            # Calculate indicator signals
            indicator_func = indicators[indicator_name]
            signals_df = indicator_func(
                st.session_state.current_data, selected_symbol, timeframe
            )

            # Convert signals to the format we need
            st.session_state.indicator_signals = [
                {
                    "timestamp": pd.to_datetime(
                        row["Sinyal Tarihi"], format="%d.%m.%Y %H:%M"
                    ),
                    "price": row["Son Fiyat"],
                    "type": row["Sinyal Türü"],
                    "indicator": indicator_name,
                }
                for _, row in signals_df.iterrows()
            ]
    elif indicator_name == "None":
        st.session_state.active_indicator = None
        st.session_state.indicator_signals = []

    # Moving Averages section in sidebar
    st.sidebar.subheader("Moving Averages")

    # Add new MA button
    if st.sidebar.button("Add Moving Average"):
        st.session_state.ma_counter += 1

    # Display existing MAs and add new ones
    ma_to_remove = None
    for i in range(st.session_state.ma_counter):
        with st.sidebar.expander(f"Moving Average #{i+1}", expanded=True):
            col1, col2 = st.columns(2)

            # MA Type selection
            ma_type = col1.selectbox("Type", ["SMA", "EMA"], key=f"ma_type_{i}")

            # Period input
            period = col2.number_input(
                "Period", min_value=1, value=20, key=f"ma_period_{i}"
            )

            # Color picker
            color = st.color_picker("Color", "#ff0000", key=f"ma_color_{i}")

            # Remove button
            if st.button("Remove", key=f"remove_ma_{i}"):
                ma_to_remove = i

            # Update or add MA to the list
            if i < len(st.session_state.moving_averages):
                st.session_state.moving_averages[i] = {
                    "type": ma_type,
                    "period": period,
                    "color": color,
                }
            else:
                st.session_state.moving_averages.append(
                    {"type": ma_type, "period": period, "color": color}
                )

    # Remove MA if requested
    if ma_to_remove is not None:
        st.session_state.moving_averages.pop(ma_to_remove)
        st.session_state.ma_counter -= 1
        st.rerun()

    # Display current balance and add balance update form
    current_balance = get_user_balance(st.session_state.user_id)
    st.sidebar.write(f"Current Balance: ${current_balance:.2f}")
    
    with st.sidebar.expander("Update Balance"):
        with st.form("update_balance_form"):
            new_balance = st.number_input("Enter new balance:", 
                                        min_value=0.0, 
                                        value=float(current_balance))
            submit_balance = st.form_submit_button("Update Balance")
            
            if submit_balance:
                update_user_balance(st.session_state.user_id, new_balance)
                st.success(f"Balance updated to ${new_balance:.2f}")
                st.rerun()

    if st.sidebar.button("Fetch Data"):
        try:
            with st.spinner("Fetching data..."):
                exchange = EXCHANGE_MAPPINGS.get(market)
                interval = get_interval(timeframe)
                full_symbol = get_full_symbol(market, selected_symbol)

                data = fetch_market_data(full_symbol, exchange, interval)

                if data is not None and not data.empty:
                    st.session_state.current_data = data

                    # Önceki işlemleri yükle
                    conn = sqlite3.connect("trading.db")
                    transactions_df = pd.read_sql_query(
                        """
                        SELECT type, chart_timestamp, price
                        FROM transactions 
                        WHERE user_id = ? AND symbol = ? AND market = ?
                        ORDER BY chart_timestamp
                        """,
                        conn,
                        params=(st.session_state.user_id, selected_symbol, market),
                    )
                    conn.close()

                    # trades listesini güncelle
                    st.session_state.trades = [
                        {
                            "type": row["type"],
                            "timestamp": pd.to_datetime(row["chart_timestamp"]),
                            "price": row["price"],
                        }
                        for _, row in transactions_df.iterrows()
                    ]

                    # Aktif indikatör varsa sinyalleri hesapla
                    if (
                        st.session_state.active_indicator
                        and st.session_state.active_indicator != "None"
                    ):
                        indicator_func = indicators[st.session_state.active_indicator]
                        signals_df = indicator_func(data, selected_symbol, timeframe)

                        # İndikatör sinyallerini güncelle
                        st.session_state.indicator_signals = [
                            {
                                "timestamp": pd.to_datetime(
                                    row["Sinyal Tarihi"], format="%d.%m.%Y %H:%M"
                                ),
                                "price": row["Son Fiyat"],
                                "type": row["Sinyal Türü"],
                                "indicator": st.session_state.active_indicator,
                            }
                            for _, row in signals_df.iterrows()
                        ]

                    st.session_state.chart_key = "main_chart"
                    display_statistics(data)
                else:
                    st.error("No data available for the selected symbol")
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")

    # Display chart if data exists
    if "current_data" in st.session_state:
        show_portfolio = st.checkbox("Show Portfolio")
        update_chart(
            st.session_state.current_data,
            selected_symbol,
            timeframe,
            st.session_state.cutoff_index,
            container=chart_container,
            key=f"main_chart_{st.session_state.cutoff_index if st.session_state.cutoff_index else 'full'}",
        )

    # Trading functionality
    if "current_data" in st.session_state:
        with trading_container:
            col1, col2, col3, col4, col5 = st.columns(5)

            # Trading forms
            with st.form(key="trading_form"):
                cols = st.columns(5)
                random_point = cols[0].form_submit_button("Show Random Point")
                plus_one = cols[1].form_submit_button("+1 Bar")
                plus_five = cols[2].form_submit_button("+5 Bars")
                buy_button = cols[3].form_submit_button("BUY")
                sell_button = cols[4].form_submit_button("SELL")

                if random_point or plus_one or plus_five or buy_button or sell_button:
                    # Save current chart layout before action
                    if st.session_state.chart_layout is None:
                        st.session_state.chart_layout = {}

                if random_point:
                    data = st.session_state.current_data
                    min_idx = int(len(data) * 0.2)
                    max_idx = int(len(data) * 0.8)
                    st.session_state.cutoff_index = random.randint(min_idx, max_idx)
                    display_statistics(data.iloc[: st.session_state.cutoff_index])

                    # Grafik güncellenmeden önce trades listesini filtrele
                    current_timestamp = data.index[st.session_state.cutoff_index - 1]
                    filtered_trades = [
                        trade
                        for trade in st.session_state.trades
                        if trade["timestamp"] <= current_timestamp
                    ]

                    st.session_state.trade_action = "random"
                    st.session_state.last_update = datetime.now()

                if plus_one and st.session_state.cutoff_index is not None:
                    st.session_state.cutoff_index += 1
                    if st.session_state.cutoff_index <= len(
                        st.session_state.current_data
                    ):
                        display_statistics(
                            st.session_state.current_data.iloc[
                                : st.session_state.cutoff_index
                            ]
                        )
                        st.session_state.trade_action = "plus_one"
                        st.session_state.last_update = datetime.now()

                if plus_five and st.session_state.cutoff_index is not None:
                    st.session_state.cutoff_index += 5
                    if st.session_state.cutoff_index <= len(
                        st.session_state.current_data
                    ):
                        display_statistics(
                            st.session_state.current_data.iloc[
                                : st.session_state.cutoff_index
                            ]
                        )
                        st.session_state.trade_action = "plus_five"
                        st.session_state.last_update = datetime.now()

            # Buy form
            if buy_button or st.session_state.show_buy_input:
                st.session_state.show_buy_input = True
                st.session_state.show_sell_input = False

                with st.form(key="buy_form"):
                    current_price = st.session_state.current_data["close"].iloc[
                        st.session_state.cutoff_index - 1
                    ]
                    max_possible_quantity = current_balance / current_price

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        quantity = st.number_input(
                            "Enter quantity to buy:", min_value=0.0
                        )
                    with col2:
                        use_max = st.checkbox(
                            "Maximum",
                            help=f"Buy maximum possible quantity ({max_possible_quantity:.4f})",
                        )

                    submit_buy = st.form_submit_button("Confirm Buy")

                    if submit_buy:
                        if use_max:
                            quantity = max_possible_quantity

                        if quantity <= 0:
                            st.error("Please enter a quantity greater than 0!")
                        else:
                            total_cost = quantity * current_price
                            if total_cost <= current_balance:
                                # Check if asset already exists
                                conn = sqlite3.connect("trading.db")
                                c = conn.cursor()
                                c.execute(
                                    """SELECT quantity, avg_price, total_cost FROM assets 
                                       WHERE user_id = ? AND symbol = ? AND market = ?""",
                                    (st.session_state.user_id, selected_symbol, market),
                                )
                                existing_asset = c.fetchone()
                                conn.close()

                                if existing_asset:
                                    # Calculate new values for existing asset
                                    new_quantity = existing_asset[0] + quantity
                                    new_total_cost = existing_asset[2] + total_cost
                                    new_avg_price = new_total_cost / new_quantity
                                else:
                                    # New asset values
                                    new_quantity = quantity
                                    new_avg_price = current_price
                                    new_total_cost = total_cost

                                update_user_balance(
                                    st.session_state.user_id,
                                    current_balance - total_cost,
                                )

                                chart_timestamp = st.session_state.current_data.index[
                                    st.session_state.cutoff_index - 1
                                ]
                                add_transaction(
                                    st.session_state.user_id,
                                    selected_symbol,
                                    "BUY",
                                    quantity,
                                    current_price,
                                    total_cost,
                                    0,
                                    market,
                                    chart_timestamp,
                                )

                                update_asset(
                                    st.session_state.user_id,
                                    selected_symbol,
                                    new_quantity,
                                    new_avg_price,
                                    new_total_cost,
                                    market,
                                )

                                st.session_state.trades.append(
                                    {
                                        "type": "BUY",
                                        "timestamp": st.session_state.current_data.index[
                                            st.session_state.cutoff_index - 1
                                        ],
                                        "price": current_price,
                                    }
                                )

                                update_chart(
                                    st.session_state.current_data,
                                    selected_symbol,
                                    timeframe,
                                    st.session_state.cutoff_index,
                                    chart_container,
                                    key=f"buy_chart_{st.session_state.cutoff_index}_{random.randint(0, 1000)}",
                                )
                                st.session_state.trade_action = "buy"
                                st.session_state.show_buy_input = False
                                st.session_state.last_update = datetime.now()
                            else:
                                st.error("Insufficient balance!")

            # Sell form
            if sell_button or st.session_state.show_sell_input:
                st.session_state.show_sell_input = True
                st.session_state.show_buy_input = False

                conn = sqlite3.connect("trading.db")
                c = conn.cursor()
                c.execute(
                    """SELECT quantity, avg_price FROM assets 
                           WHERE user_id = ? AND symbol = ? AND market = ?""",
                    (st.session_state.user_id, selected_symbol, market),
                )
                position = c.fetchone()
                conn.close()

                if position and position[0] > 0:
                    with st.form(key="sell_form"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            quantity = st.number_input(
                                "Enter quantity to sell:",
                                min_value=0.0,
                                max_value=position[0],
                            )
                        with col2:
                            use_max = st.checkbox(
                                "Maximum", help=f"Sell all holdings ({position[0]:.4f})"
                            )

                        submit_sell = st.form_submit_button("Confirm Sell")

                        if submit_sell:
                            if use_max:
                                quantity = position[0]

                            if quantity <= 0:
                                st.error("Please enter a quantity greater than 0!")
                            else:
                                current_price = st.session_state.current_data[
                                    "close"
                                ].iloc[st.session_state.cutoff_index - 1]
                                total_amount = quantity * current_price
                                profit_loss = (current_price - position[1]) * quantity

                                update_user_balance(
                                    st.session_state.user_id,
                                    current_balance + total_amount,
                                )

                                chart_timestamp = st.session_state.current_data.index[
                                    st.session_state.cutoff_index - 1
                                ]
                                add_transaction(
                                    st.session_state.user_id,
                                    selected_symbol,
                                    "SELL",
                                    quantity,
                                    current_price,
                                    total_amount,
                                    profit_loss,
                                    market,
                                    chart_timestamp,
                                )

                                update_asset(
                                    st.session_state.user_id,
                                    selected_symbol,
                                    position[0] - quantity,
                                    position[1],
                                    position[1] * (position[0] - quantity),
                                    market,
                                )

                                st.session_state.trades.append(
                                    {
                                        "type": "SELL",
                                        "timestamp": st.session_state.current_data.index[
                                            st.session_state.cutoff_index - 1
                                        ],
                                        "price": current_price,
                                    }
                                )

                                update_chart(
                                    st.session_state.current_data,
                                    selected_symbol,
                                    timeframe,
                                    st.session_state.cutoff_index,
                                    chart_container,
                                    key=f"sell_chart_{st.session_state.cutoff_index}_{random.randint(0, 1000)}",
                                )
                                st.session_state.trade_action = "sell"
                                st.session_state.show_sell_input = False
                                st.session_state.last_update = datetime.now()
                else:
                    st.error("No position to sell!")
                    st.session_state.show_sell_input = False

            # Update chart based on trade action
            if st.session_state.trade_action:
                current_layout = st.session_state.chart_layout
                update_chart(
                    st.session_state.current_data,
                    selected_symbol,
                    timeframe,
                    st.session_state.cutoff_index,
                    chart_container,
                    key=f"chart_{st.session_state.trade_action}_{st.session_state.last_update.timestamp()}",
                )
                st.session_state.chart_layout = current_layout
                st.session_state.trade_action = None

        # Portfolio display
        if show_portfolio:
            with portfolio_container:
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Current Positions")
                    conn = sqlite3.connect("trading.db")
                    positions_df = pd.read_sql_query(
                        """
                        SELECT symbol, quantity, avg_price, total_cost, market
                        FROM assets 
                        WHERE user_id = ? AND quantity > 0
                    """,
                        conn,
                        params=(st.session_state.user_id,),
                    )
                    conn.close()

                    if not positions_df.empty:
                        st.dataframe(positions_df)
                    else:
                        st.info("No active positions")

                with col2:
                    st.subheader("Transaction History")
                    conn = sqlite3.connect("trading.db")
                    transactions_df = pd.read_sql_query(
                        """
                        SELECT symbol, type, quantity, price, total_amount, 
                               profit_loss, timestamp, chart_timestamp, market
                        FROM transactions 
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """,
                        conn,
                        params=(st.session_state.user_id,),
                    )
                    conn.close()

                    if not transactions_df.empty:
                        st.dataframe(transactions_df)
                    else:
                        st.info("No transactions yet")


if __name__ == "__main__":
    init_db()
    init_user(1)  # Demo user'ı başlat
    main()
