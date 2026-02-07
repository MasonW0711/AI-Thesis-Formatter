import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: '論文格式調整系統',
    description: '自動將您的論文調整為符合學校規定的格式',
    keywords: ['論文', '格式調整', '排版', '學術論文'],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="zh-TW">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body>
                <div className="page-wrapper">
                    <header className="header">
                        <div className="container header-content">
                            <a href="/" className="logo">
                                <span className="logo-icon">📄</span>
                                <span>論文格式調整系統</span>
                            </a>
                            <nav className="nav-links">
                                <a href="/" className="nav-link">首頁</a>
                                <a href="/upload" className="nav-link">上傳文件</a>
                                <a href="/documents" className="nav-link">我的文件</a>
                            </nav>
                        </div>
                    </header>

                    <main className="main-content">
                        {children}
                    </main>

                    <footer className="footer">
                        <div className="container footer-content">
                            <p className="footer-text">
                                © 2026 論文格式調整系統 — Spec v1
                            </p>
                            <p className="footer-text">
                                讓您的論文格式完美符合學校規定
                            </p>
                        </div>
                    </footer>
                </div>
            </body>
        </html>
    );
}
