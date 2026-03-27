import Dashboard from "@/components/dashboard";
import { fetchDashboardData } from "@/lib/api";

export default async function Home() {
  const dashboardData = await fetchDashboardData();

  return <Dashboard {...dashboardData} />;
}
