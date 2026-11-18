export interface HealthCountry {
    iso3: string;
    iso2: string | null;
    name: string;
    region: string | null;
    income_level: string | null;
}

export interface HealthIndicator {
    code: string;
    name: string;
    definition: string;
    unit: string;
    source: string;
    latest_year: number | null;
    publisher?: string | null;
    definition_url?: string | null;
    dataset_code?: string | null;
    dataset_name?: string | null;
    dataset_version?: string | null;
}

export interface HealthObservation {
    country_iso3: string;
    country_name: string;
    indicator_code: string;
    indicator_name: string;
    value: number;
    year: number;
    unit: string;
    source: string;
    imported_at: string;
    source_reference?: string | null;
    source_publication_date?: string | null;
    source_record_timestamp?: string | null;
    source_value_text?: string | null;
    denominator_value?: number | null;
    denominator_definition?: string | null;
    dimensions?: Record<string, string> | null;
    uncertainty_lower?: number | null;
    uncertainty_upper?: number | null;
    estimate_status?: string | null;
}

export interface HealthDataCoverage {
    indicator_code: string;
    country_iso3: string;
    country_name: string;
    observation_count: number;
    first_year: number;
    last_year: number;
    observed_years: number[];
    unobserved_years_within_span: number[];
    cadence_note: string;
}

export interface HealthObservationSet {
    indicator: HealthIndicator;
    year: number | null;
    observations: HealthObservation[];
}

export interface HealthCountryObservationSet {
    country: HealthCountry;
    observations: HealthObservation[];
}

export interface TrendSeries {
    country: HealthCountry;
    observations: HealthObservation[];
    change_from_year: number | null;
    change_to_year: number | null;
    absolute_change: number | null;
    percent_change: number | null;
}

export interface TrendAnalysis {
    indicator: HealthIndicator;
    start_year: number;
    end_year: number;
    series: TrendSeries[];
}

export interface ComparisonCountry {
    country: HealthCountry;
    observation: HealthObservation | null;
    difference_from_reference: number | null;
    percent_difference_from_reference: number | null;
}

export interface CountryComparison {
    indicator: HealthIndicator;
    year: number;
    reference_iso3: string;
    countries: ComparisonCountry[];
}

export interface IndicatorRankingRow {
    rank: number;
    observation: HealthObservation;
}

export interface IndicatorRanking {
    indicator: HealthIndicator;
    year: number;
    order: "ascending" | "descending";
    rows: IndicatorRankingRow[];
}

export type MapPosition = [number, number];

export interface MapPolygonGeometry {
    type: "Polygon";
    coordinates: MapPosition[][];
}

export interface MapMultiPolygonGeometry {
    type: "MultiPolygon";
    coordinates: MapPosition[][][];
}

export interface WorldMapFeature {
    type: "Feature";
    properties: Record<string, string>;
    geometry: MapPolygonGeometry | MapMultiPolygonGeometry | null;
}

export interface WorldMapData {
    type: "FeatureCollection";
    features: WorldMapFeature[];
}
