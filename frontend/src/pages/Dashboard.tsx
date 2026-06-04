import { useState } from "react";
import { getCountryProfile } from "../services/healthApi";
import type { HealthProfile } from "../types/HealthProfile";

function Dashboard() {
const [country, setCountry] = useState("Philippines");

const [profile, setProfile] =
    useState<HealthProfile | null>(null);

const loadCountry = async () => {
    const response = await getCountryProfile(country);
    setProfile(response.data);
};

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
        <div className="profile-card">
            <h2>{profile.country}</h2>

            <p>
                Population:
                {" "}
                {profile.population.toLocaleString()}
            </p>

            <p>
                Health Index: {profile.health_index}
            </p>

            <p>
                Recovery Rate:
                {" "}
                {profile.recovery_rate}%
            </p>

            <p>
                Mortality Rate:
                {" "}
                {profile.mortality_rate}%
            </p>
        </div>
    )}
    </div>
);
}

export default Dashboard;