'use client';

import Link from 'next/link';

export default function HomePage() {
    return (
        <>
            {/* Hero Section */}
            <section className="hero">
                <div className="container hero-content">
                    <h1>論文格式調整系統</h1>
                    <p>
                        自動將您的論文調整為符合學校規定的格式，節省大量手動編排的時間與精力
                    </p>
                    <Link href="/upload" className="btn btn-primary btn-lg">
                        📤 開始上傳論文
                    </Link>
                </div>
            </section>

            {/* Features Section */}
            <section className="container" style={{ padding: '4rem 1.5rem' }}>
                <h2 className="text-center mb-6">主要功能</h2>

                <div className="template-grid">
                    <div className="card animate-fade-in">
                        <div className="card-header">
                            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📤</div>
                            <h3 className="card-title">上傳 PDF 文件</h3>
                        </div>
                        <p className="card-description">
                            支援拖放上傳，輕鬆將您的論文 PDF 檔案上傳至系統
                        </p>
                    </div>

                    <div className="card animate-fade-in" style={{ animationDelay: '0.1s' }}>
                        <div className="card-header">
                            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🔍</div>
                            <h3 className="card-title">智能格式分析</h3>
                        </div>
                        <p className="card-description">
                            自動識別論文結構，包括標題、段落、引用等元素
                        </p>
                    </div>

                    <div className="card animate-fade-in" style={{ animationDelay: '0.2s' }}>
                        <div className="card-header">
                            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>✨</div>
                            <h3 className="card-title">自動格式調整</h3>
                        </div>
                        <p className="card-description">
                            根據學校規定的格式範本，自動調整排版格式
                        </p>
                    </div>

                    <div className="card animate-fade-in" style={{ animationDelay: '0.3s' }}>
                        <div className="card-header">
                            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📥</div>
                            <h3 className="card-title">一鍵下載</h3>
                        </div>
                        <p className="card-description">
                            處理完成後，輕鬆下載調整後的論文檔案
                        </p>
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section style={{ background: 'var(--gray-100)', padding: '4rem 0' }}>
                <div className="container">
                    <h2 className="text-center mb-6">使用流程</h2>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '2rem',
                        textAlign: 'center'
                    }}>
                        <div>
                            <div style={{
                                width: '64px',
                                height: '64px',
                                margin: '0 auto 1rem',
                                background: 'var(--gradient-primary)',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontSize: '1.5rem',
                                fontWeight: '700'
                            }}>1</div>
                            <h4>上傳論文</h4>
                            <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                                將您的 PDF 論文檔案上傳至系統
                            </p>
                        </div>

                        <div>
                            <div style={{
                                width: '64px',
                                height: '64px',
                                margin: '0 auto 1rem',
                                background: 'var(--gradient-primary)',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontSize: '1.5rem',
                                fontWeight: '700'
                            }}>2</div>
                            <h4>選擇格式</h4>
                            <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                                選擇符合學校規定的格式範本
                            </p>
                        </div>

                        <div>
                            <div style={{
                                width: '64px',
                                height: '64px',
                                margin: '0 auto 1rem',
                                background: 'var(--gradient-primary)',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontSize: '1.5rem',
                                fontWeight: '700'
                            }}>3</div>
                            <h4>自動處理</h4>
                            <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                                系統自動分析並調整論文格式
                            </p>
                        </div>

                        <div>
                            <div style={{
                                width: '64px',
                                height: '64px',
                                margin: '0 auto 1rem',
                                background: 'var(--gradient-primary)',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontSize: '1.5rem',
                                fontWeight: '700'
                            }}>4</div>
                            <h4>下載成果</h4>
                            <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                                下載格式調整完成的論文
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="container" style={{ padding: '4rem 1.5rem', textAlign: 'center' }}>
                <h2>準備好了嗎？</h2>
                <p style={{ color: 'var(--gray-500)', marginBottom: '2rem' }}>
                    立即上傳您的論文，讓我們幫您處理繁瑣的格式調整工作
                </p>
                <Link href="/upload" className="btn btn-primary btn-lg">
                    開始使用 →
                </Link>
            </section>
        </>
    );
}
