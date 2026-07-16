// Barrel for the reusable usage components (P4.S3). Both are presentational,
// props-only server components generic over vocky's metrics shapes, which are
// identical for the tenant aggregate (`GET /app/usage`) and one project's
// drill-down (`GET /app/projects/{id}/usage`) — so P4.S4's project page renders
// its own usage with these same two components.
export { StatTiles } from "./stat-tiles";
export type { StatTilesProps } from "./stat-tiles";

export { TrendChart } from "./trend-chart";
export type { TrendChartProps } from "./trend-chart";
