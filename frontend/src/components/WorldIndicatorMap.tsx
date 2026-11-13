import { useMemo, useState, type MouseEvent } from "react";

import type {
    HealthCountry,
    HealthIndicator,
    HealthObservation,
    WorldMapData,
    WorldMapFeature,
    MapPosition,
} from "../types/HealthIndicator";

interface WorldIndicatorMapProps {
    geography: WorldMapData;
    countries: HealthCountry[];
    indicator: HealthIndicator;
    year: number;
    observations: HealthObservation[];
    selectedCountry: string | null;
    onSelectCountry: (iso3: string, name: string) => void;
}

interface HoveredCountry {
    name: string;
    value: number | null;
    x: number;
    y: number;
}

const COLORS = ["#dbeafe", "#93c5fd", "#3b82f6", "#1d4ed8", "#172554"];
const NO_DATA_COLOR = "#475569";

function countryCode(feature: WorldMapFeature): string | null {
    const properties = feature.properties;
    const code = properties.ISO_A3_EH || properties.ISO_A3 || properties.ADM0_A3;
    return code && /^[A-Z]{3}$/.test(code) ? code : null;
}

function countryName(feature: WorldMapFeature): string {
    return feature.properties.ADMIN || feature.properties.NAME || "Unknown country";
}

function project([longitude, latitude]: MapPosition): [number, number] {
    return [(longitude + 180) * (1000 / 360), (90 - latitude) * (500 / 180)];
}

function polygonPath(
    rings: MapPosition[][],
): string {
    return rings.map((ring) => ring.map((point, index) => {
        const [x, y] = project(point);
        return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(" ") + " Z").join(" ");
}

function featurePath(feature: WorldMapFeature): string {
    const geometry = feature.geometry;
    if (!geometry) return "";
    const polygons = geometry.type === "Polygon"
        ? [geometry.coordinates]
        : geometry.coordinates;
    return polygons.map(polygonPath).join(" ");
}

function formatValue(value: number, unit: string): string {
    const formatted = new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 2,
    }).format(value);
    return unit === "%" ? `${formatted}%` : `${formatted} ${unit}`;
}

export default function WorldIndicatorMap({
    geography,
    countries,
    indicator,
    year,
    observations,
    selectedCountry,
    onSelectCountry,
}: WorldIndicatorMapProps) {
    const [hoveredCountry, setHoveredCountry] = useState<HoveredCountry | null>(null);
    const [zoom, setZoom] = useState(1);
    const values = useMemo(
        () => new Map(observations.map((observation) => [
            observation.country_iso3,
            observation.value,
        ])),
        [observations],
    );
    const bounds = useMemo(() => {
        const numbers = observations.map(({ value }) => value);
        return {
            minimum: Math.min(...numbers),
            maximum: Math.max(...numbers),
        };
    }, [observations]);

    const colorFor = (value: number | undefined) => {
        if (value === undefined) return NO_DATA_COLOR;
        if (bounds.maximum === bounds.minimum) return COLORS[2];
        const position = (value - bounds.minimum) / (bounds.maximum - bounds.minimum);
        return COLORS[Math.min(COLORS.length - 1, Math.floor(position * COLORS.length))];
    };

    const handleHover = (
        event: MouseEvent<SVGPathElement>,
        feature: WorldMapFeature,
        iso3: string | null,
    ) => {
        const rectangle = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
        if (!rectangle) return;
        setHoveredCountry({
            name: countryName(feature),
            value: iso3 ? values.get(iso3) ?? null : null,
            x: event.clientX - rectangle.left + 12,
            y: event.clientY - rectangle.top + 12,
        });
    };

    const colorStep = bounds.maximum === bounds.minimum
        ? null
        : (bounds.maximum - bounds.minimum) / COLORS.length;

    return (
        <div className="world-map-layout">
            <div className="world-map" onMouseLeave={() => setHoveredCountry(null)}>
                <label className="map-country-select">
                    Select any country
                    <select
                        aria-label="Select any country"
                        value={selectedCountry ?? ""}
                        onChange={(event) => {
                            const country = countries.find(
                                (item) => item.iso3 === event.target.value,
                            );
                            if (country) onSelectCountry(country.iso3, country.name);
                        }}
                    >
                        <option value="">Choose a country…</option>
                        {countries.map((country) => (
                            <option key={country.iso3} value={country.iso3}>
                                {country.name} ({country.iso3})
                            </option>
                        ))}
                    </select>
                </label>
                <div className="map-zoom-controls" role="group" aria-label="Map zoom controls">
                    <button
                        type="button"
                        aria-label="Zoom in on map"
                        disabled={zoom >= 4}
                        onClick={() => setZoom((current) => Math.min(4, current + 0.5))}
                    >
                        +
                    </button>
                    <button
                        type="button"
                        aria-label="Zoom out on map"
                        disabled={zoom <= 1}
                        onClick={() => setZoom((current) => Math.max(1, current - 0.5))}
                    >
                        −
                    </button>
                    <button
                        type="button"
                        aria-label="Reset map zoom"
                        disabled={zoom === 1}
                        onClick={() => setZoom(1)}
                    >
                        Reset
                    </button>
                </div>
                <svg
                    viewBox="0 0 1000 500"
                    role="img"
                    aria-label={`${indicator.name} by country for ${year}`}
                >
                    <g transform={`translate(${-500 * (zoom - 1)} ${-250 * (zoom - 1)}) scale(${zoom})`}>
                        {geography.features.map((feature, index) => {
                            const iso3 = countryCode(feature);
                            const name = countryName(feature);
                            const value = iso3 ? values.get(iso3) : undefined;
                            const selected = iso3 !== null && iso3 === selectedCountry;
                            return (
                                <path
                                    key={`${iso3 ?? name}-${index}`}
                                    d={featurePath(feature)}
                                    fill={colorFor(value)}
                                    className={selected ? "world-map-country selected" : "world-map-country"}
                                    role={iso3 ? "button" : undefined}
                                    tabIndex={iso3 ? 0 : undefined}
                                    aria-label={`${name}: ${value === undefined ? "No data" : formatValue(value, indicator.unit)}`}
                                    onMouseMove={(event) => handleHover(event, feature, iso3)}
                                    onMouseEnter={(event) => handleHover(event, feature, iso3)}
                                    onClick={() => {
                                        if (iso3) onSelectCountry(iso3, name);
                                    }}
                                    onKeyDown={(event) => {
                                        if (iso3 && (event.key === "Enter" || event.key === " ")) {
                                            event.preventDefault();
                                            onSelectCountry(iso3, name);
                                        }
                                    }}
                                />
                            );
                        })}
                    </g>
                </svg>
                {hoveredCountry && (
                    <div
                        className="world-map-tooltip"
                        style={{ left: hoveredCountry.x, top: hoveredCountry.y }}
                        role="status"
                    >
                        <strong>{hoveredCountry.name}</strong>
                        <span>
                            {hoveredCountry.value === null
                                ? "No data"
                                : formatValue(hoveredCountry.value, indicator.unit)}
                            {" · "}{year}
                        </span>
                    </div>
                )}
            </div>
            <div className="map-legend" aria-label="Map color legend">
                <div className="map-legend-heading">
                    <strong>{indicator.name}</strong>
                    <span>{indicator.unit}</span>
                </div>
                <div className="map-legend-gradient" aria-hidden="true">
                    {COLORS.map((color) => (
                        <span key={color} style={{ backgroundColor: color }} />
                    ))}
                </div>
                <div className="map-legend-labels">
                    <span>{observations.length ? formatValue(bounds.minimum, indicator.unit) : "No observations"}</span>
                    <span>{observations.length ? formatValue(bounds.maximum, indicator.unit) : ""}</span>
                </div>
                <div className="map-no-data-label">
                    <span className="map-no-data-swatch" />
                    No data
                </div>
                {colorStep !== null && observations.length > 0 && (
                    <div className="map-legend-breaks">
                        {COLORS.map((color, index) => {
                            const low = bounds.minimum + colorStep * index;
                            const high = index === COLORS.length - 1
                                ? bounds.maximum
                                : bounds.minimum + colorStep * (index + 1);
                            return (
                                <span key={color}>
                                    {formatValue(low, indicator.unit)}–{formatValue(high, indicator.unit)}
                                </span>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
