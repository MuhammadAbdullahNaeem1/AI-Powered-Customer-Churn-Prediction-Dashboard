import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata = {
  title: "Churn Radar — Customer Churn Dashboard",
  description: "Monitor customer churn risk and act on high-risk accounts.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 min-w-0 lg:ml-64">
            <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
