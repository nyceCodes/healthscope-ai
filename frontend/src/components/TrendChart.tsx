import {
LineChart,
Line,
XAxis,
YAxis,
CartesianGrid,
Tooltip,
ResponsiveContainer
} from "recharts";

interface TrendData {
date: string;
health_index: number;
}

interface Props {
data: TrendData[];
}

function TrendChart({ data }: Props) {
return (
    <ResponsiveContainer
    width="100%"
    height={300}
    >
    <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />

        <XAxis
            dataKey="date"
            tickFormatter={(value) =>
                new Date(value).toLocaleTimeString(
                    [],
                    {
                        hour: "2-digit",
                        minute: "2-digit"
                    }
                )
            }
        />
        <YAxis />

        <Tooltip />

        <Line
        type="monotone"
        dataKey="health_index"
        />
    </LineChart>
    </ResponsiveContainer>
);
}

export default TrendChart;