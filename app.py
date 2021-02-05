import datetime

import streamlit as st
import pandas
import joblib

from nba import br_extractor, preprocess, evaluate

# Constants
logo_url = "https://i.jebbit.com/images/k9VpjZfZ/business-images/41hdlnbMRJSZe152NgYk_KIA_PerfAwards_MVP.png"
year = datetime.datetime.now().year

# Page properties
st.set_page_config(page_title='NBA MVP Prediction', page_icon = logo_url, layout = 'centered', initial_sidebar_state = 'auto')
st.title(f'Predicting the MVP.')

# Functions
@st.cache
def load_player_stats(season):
    extractor = br_extractor.BRExtractor()
    stats = extractor.get_player_stats(subset_by_seasons=[season], subset_by_stat_types=['per_game', 'per_36min', 'per_100poss', 'advanced'])
    stats.to_csv("./data/current_player_stats.csv")
    return stats
@st.cache
def load_team_stats(season):
    extractor = br_extractor.BRExtractor()
    stats = extractor.get_team_standings(subset_by_seasons=[season])
    stats.to_csv("./data/current_team_stats.csv")
    return stats
@st.cache
def consolidate_stats(team_stats, player_stats):
    player_stats["SEASON"] = player_stats["SEASON"].astype(int)
    team_stats["SEASON"] = team_stats["SEASON"].astype(int)
    stats = player_stats.merge(team_stats, how='inner', on=["TEAM", "SEASON"])
    #stats = stats.set_index("player_season_team", drop=True)
    stats.to_csv("./data/current_consolidated_raw.csv")
    return stats
def load_2020_preds():
    preds = pandas.read_csv("./static/data/2020_dataset_predictions.csv")
    return preds
def load_test_preds():
    preds = pandas.read_csv("./static/data/test_dataset_predictions.csv")
    return preds
def mvp_found_pct(test_dataset_predictions):
    metrics = (test_dataset_predictions["Pred. MVP"] == test_dataset_predictions["True MVP"]).sum() / len(test_dataset_predictions)
    metrics = int(metrics*100)
    return str(metrics) + " %"
def avg_real_mvp_rank(test_dataset_predictions):
    metrics = (test_dataset_predictions["REAL_RANK"]).mean()
    return "%.2f" % metrics
def clean_data(data):
    #TODO : reuse cleaning process
    return data.fillna(0.0)

def predict(data, model):
    cat = ['POS', 'CONF']
    num = ['2P%', '2P_per_game', '3P%', '3PAR_advanced', '3PA_per_game', 'AGE', 'AST%_advanced', 'BLK_per_36min', 'DBPM_advanced', 'DRB_per_game', 'DRTG_per_100poss', 'DWS_advanced', 'FG%', 'FG_per_100poss', 'FT%', 'FTR_advanced', 'FT_per_game', 'G', 'MP', 'OBPM_advanced', 'ORB%_advanced', 'ORTG_per_100poss', 'OWS_advanced', 'PF_per_36min', 'PF_per_game', 'PTS_per_game', 'STL_per_game', 'TOV%_advanced', 'TOV_per_36min', 'TOV_per_game', 'TRB_per_36min', 'TS%_advanced', 'WS/48_advanced', 'GB', 'PW', 'PL', 'PA/G', 'CONF_RANK']
    min_max_scaling = True
    data_processed_features_only, _ = preprocess.scale_per_value_of(data, cat, num, data["SEASON"], min_max_scaler=min_max_scaling)
    features =  ['FG_per_100poss', 'MP', 'FTR_advanced', 'PF_per_36min', '3P%',
       'TRB_per_36min', 'DWS_advanced', 'AST%_advanced', 'TS%_advanced', '2P%',
       'CONF_RANK', 'OBPM_advanced', 'FT%', 'GB', 'FT_per_game', 'PW', 'FG%',
       'PA/G', 'AGE', 'PF_per_game', 'OWS_advanced', 'TOV_per_36min',
       'TOV%_advanced', 'TOV_per_game', 'ORB%_advanced', 'G', 'WS/48_advanced',
       '3PAR_advanced', 'PL', 'DRB_per_game', 'PTS_per_game', '2P_per_game',
       'STL_per_game', 'BLK_per_36min', 'ORTG_per_100poss', 'DRTG_per_100poss',
       '3PA_per_game', 'DBPM_advanced', 'POS_C', 'POS_PF', 'POS_PG', 'POS_SF',
       'POS_SG', 'CONF_EASTERN_CONF', 'CONF_WESTERN_CONF']
    X = data_processed_features_only[features]
    preds = model.predict(X)
    return preds

# Init page
current_team_stats = load_team_stats(year).copy()
current_player_stats = load_player_stats(year).copy()
current_consolidated_raw = consolidate_stats(current_team_stats, current_player_stats)
preds_2020 = load_2020_preds()
preds_test = load_test_preds()
num_test_seasons = len(preds_test)
mvp_found_pct = mvp_found_pct(preds_test)
avg_real_mvp_rank = avg_real_mvp_rank(preds_test)
model = joblib.load('static/model/model.joblib')
dataset = clean_data(current_consolidated_raw)
# Predict
initial_columns = list(dataset.columns)
predictions = predict(dataset, model)
dataset.loc[:, "PRED"] = predictions
dataset.loc[:, "PRED_RANK"] = dataset["PRED"].rank(ascending=False)
dataset.loc[dataset.PRED_RANK <= 10., "CONFIDENCEv1"] = evaluate.softmax(dataset[dataset.PRED_RANK <= 10.]["PRED"]) * 100
dataset.loc[dataset.PRED_RANK > 10., "CONFIDENCEv1"] = 0.
dataset.loc[dataset.PRED_RANK <= 10., "CONFIDENCEv2"] = evaluate.share(dataset[dataset.PRED_RANK <= 10.]["PRED"]) * 100
dataset.loc[dataset.PRED_RANK > 10., "CONFIDENCEv2"] = 0.
dataset["CONFIDENCEv1"] = dataset["CONFIDENCEv1"].map('{:,.2f}%'.format)
dataset["CONFIDENCEv2"] = dataset["CONFIDENCEv2"].map('{:,.2f}%'.format)
dataset = dataset[["CONFIDENCEv1", "CONFIDENCEv2"] + initial_columns]
dataset = dataset.sort_values(by="PRED", ascending=False)

# Sidebar
st.sidebar.image(logo_url, width=100, clamp=False, channels='RGB', output_format='auto')
st.sidebar.text(f"Season : {year-1}-{year}")
st.sidebar.markdown(f'''
**Predicting the NBA Most Valuable Player using machine learning.**

Expected performance of the model, as calculated on the test set ({num_test_seasons} seasons):
- **{mvp_found_pct}** of MVPs correctly found
- Real MVP is ranked in average **{avg_real_mvp_rank}**

*Made by [pauldes](https://github.com/pauldes). Code on [GitHub](https://github.com/pauldes/nba-mvp-prediction).*
''')

# Main content
st.header("Current year predictions")
st.dataframe(data=dataset.head(10), width=None, height=None)
st.header("Data retrieved")
st.subheader("Player stats")
st.markdown('''
These stats describe the player individual accomplishments.
''')
st.dataframe(data=current_player_stats.sample(10), width=None, height=None)
st.subheader("Team stats")
st.markdown('''
These stats describe the team accomplishments.
''')
st.dataframe(data=current_team_stats.sample(10), width=None, height=None)
st.header("Model performance")
st.subheader(f"Test predictions ({num_test_seasons} seasons)")
st.markdown('''
Predictions of the model on the unseen, test dataset.
''')
st.markdown(f'''
- **{mvp_found_pct}** of MVPs correctly found
- Real MVP is ranked in average **{avg_real_mvp_rank}**
''')
st.dataframe(data=preds_test, width=None, height=None)
st.subheader("Year 2020")
st.markdown('''
Predictions of the model on the unseen, 2020 season dataset.
''')
st.dataframe(data=preds_2020, width=None, height=None)
