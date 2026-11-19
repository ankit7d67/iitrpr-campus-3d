import type { Metadata, Viewport } from 'next';
import { asset } from '../lib/assets';
import './globals.css';

const title = 'IIT Ropar 3D Campus';
const description =
  'Explore a low-poly 3D map of IIT Ropar’s permanent campus: find buildings, plan walking routes and take an orientation tour.';

export const metadata: Metadata = {
  // Set NEXT_PUBLIC_SITE_URL (e.g. https://<user>.github.io) when deploying so
  // the share image URL is absolute.
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title,
  description,
  applicationName: title,
  authors: [{ name: 'IIT Ropar Campus 3D' }],
  creator: 'IIT Ropar Campus 3D',
  openGraph: {
    title,
    description,
    type: 'website',
    images: [
      { url: asset('/og.jpg'), width: 1200, height: 630, alt: 'Aerial view of the 3D campus model' },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
    images: [asset('/og.jpg')],
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#115e59',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
