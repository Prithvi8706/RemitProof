import { ResearchHome } from "@/components/research/ResearchHome";
import { getBenchmark, getDashboard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [dashboard, benchmark] = await Promise.all([getDashboard(), getBenchmark()]);
  return <ResearchHome dashboard={dashboard} benchmark={benchmark} />;
}
