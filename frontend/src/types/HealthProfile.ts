export interface HealthProfile {
  country: string;

  population: number;

  region: string;

  capital: string;

  cases: number;

  deaths: number;

  recovered: number;

  active: number;

  tests: number;

  recovery_rate: number;

  mortality_rate: number;

  health_index: number;

  data_source: string;
  data_status: string;
  data_as_of: string | null;
}