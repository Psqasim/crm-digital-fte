import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ChatWidgetPortal from "@/components/chat/ChatWidgetPortal";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Navbar />
      {children}
      <Footer />
      <ChatWidgetPortal />
    </>
  );
}
