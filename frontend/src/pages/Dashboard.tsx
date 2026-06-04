import { useEffect, useState } from "react";
import { getCountryProfile, getCountryTrends, getRankings } from "../services/healthApi";
import type { HealthProfile } from "../types/HealthProfile";
import TrendChart from "../components/TrendChart";
import "../styles/dashboard.css";
import type { TrendData }
from "../types/TrendData";

import type { Ranking }
from "../types/Ranking";

function Dashboard() {
const [country, setCountry] = useState("Philippines");

const [profile, setProfile] =
    useState<HealthProfile | null>(null);

const [trendData, setTrendData] = useState<TrendData[]>([]);
const [rankings, setRankings] = useState<Ranking[]>([]);

const loadCountry = async () => {
    const response = await getCountryProfile(country);
    setProfile(response.data);

    const trendResponse = await getCountryTrends(country);
    setTrendData(trendResponse.data);
};

useEffect(() => {
    getRankings().then((res) => setRankings(res.data));
}, []);

    return (
        <div className="dashboard">
            <h1>Dashboard</h1>

    <div className="search-form">
        <input
            type="text"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="Enter a country"
        />

        <button
            type="button"
            onClick={loadCountry}
            >
            Search
        </button>
    </div>

    {profile && (
        <>
            <div className="profile-card">
                <h2>{profile.country}</h2>
                <div className="cards">
                    <div className="card">
                        <h3>Population</h3>
                        <p>{profile.population.toLocaleString()}</p>
                    </div>
                    <div className="card">
                        <h3>Health Index</h3>
                        <p>{profile.health_index}</p>
                    </div>
                    <div className="card">
                        <h3>Recovery Rate</h3>
                        <p>{profile.recovery_rate}%</p>
                    </div>
                    <div className="card">
                        <h3>Mortality Rate</h3>
                        <p>{profile.mortality_rate}%</p>
                    </div>
                </div>
            </div>

            {trendData.length > 0 && (
                <div className="trend-chart">
                    <h3>Trend</h3>
                    <TrendChart data={trendData} />
                </div>
            )}

            {rankings.length > 0 && (
                <div className="rankings-panel">
                    <h3>Top Health Rankings</h3>
                    <div className="rankings-list">
                        {rankings.slice(0, 10).map((item, index) => (
                            <div className="ranking-row" key={`${item.country}-${index}`}>
                                <span>{index + 1}.</span>
                                <span>{item.country}</span>
                                <span>{item.health_index}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    )}
    </div>
);
}

export default Dashboard;