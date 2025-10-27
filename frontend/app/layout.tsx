import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Job-MCP - Land Your Dream CS Job',
  description: 'AI-powered job applications for students',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

