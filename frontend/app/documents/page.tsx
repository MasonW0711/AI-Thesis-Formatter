'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

interface Document {
    id: number;
    filename: string;
    status: string;
    file_size: number;
    page_count: number;
    created_at: string;
}

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchDocuments = useCallback(async () => {
        try {
            const response = await fetch('/api/documents');
            if (!response.ok) {
                throw new Error('獲取文件列表失敗');
            }
            const data = await response.json();
            setDocuments(data.documents);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : '載入失敗');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDocuments();

        // 每 5 秒自動刷新（檢查處理狀態）
        const interval = setInterval(fetchDocuments, 5000);
        return () => clearInterval(interval);
    }, [fetchDocuments]);

    const handleDownload = async (doc: Document) => {
        try {
            const response = await fetch(`/api/documents/${doc.id}/download`);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || '下載失敗');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `格式調整_${doc.filename}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            alert(err instanceof Error ? err.message : '下載失敗');
        }
    };

    const handleDelete = async (doc: Document) => {
        if (!confirm(`確定要刪除「${doc.filename}」嗎？`)) return;

        try {
            const response = await fetch(`/api/documents/${doc.id}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('刪除失敗');
            }

            fetchDocuments();
        } catch (err) {
            alert(err instanceof Error ? err.message : '刪除失敗');
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const formatDate = (dateString: string): string => {
        const date = new Date(dateString);
        return date.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, { label: string; class: string }> = {
            uploaded: { label: '已上傳', class: 'status-uploaded' },
            processing: { label: '處理中', class: 'status-processing' },
            completed: { label: '已完成', class: 'status-completed' },
            failed: { label: '處理失敗', class: 'status-failed' },
        };

        const info = statusMap[status] || { label: status, class: 'status-uploaded' };
        return <span className={`status-badge ${info.class}`}>{info.label}</span>;
    };

    return (
        <div className="container" style={{ maxWidth: '900px', padding: '2rem 1.5rem' }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '2rem'
            }}>
                <h1>我的文件</h1>
                <Link href="/upload" className="btn btn-primary">
                    📤 上傳新文件
                </Link>
            </div>

            {/* 錯誤訊息 */}
            {error && (
                <div style={{
                    padding: '1rem',
                    background: 'var(--error-500)',
                    color: 'white',
                    borderRadius: 'var(--radius)',
                    marginBottom: '1.5rem',
                }}>
                    ⚠️ {error}
                </div>
            )}

            {/* 載入中 */}
            {isLoading && (
                <div className="text-center" style={{ padding: '4rem 0' }}>
                    <div style={{ fontSize: '3rem' }} className="animate-spin">⏳</div>
                    <p style={{ marginTop: '1rem', color: 'var(--gray-500)' }}>載入中...</p>
                </div>
            )}

            {/* 空狀態 */}
            {!isLoading && documents.length === 0 && (
                <div className="card text-center" style={{ padding: '4rem 2rem' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📭</div>
                    <h3>尚無文件</h3>
                    <p style={{ color: 'var(--gray-500)', marginBottom: '2rem' }}>
                        上傳您的第一份論文，開始使用格式調整功能
                    </p>
                    <Link href="/upload" className="btn btn-primary">
                        上傳論文
                    </Link>
                </div>
            )}

            {/* 文件列表 */}
            {!isLoading && documents.length > 0 && (
                <div className="file-list">
                    {documents.map((doc) => (
                        <div key={doc.id} className="file-item animate-fade-in">
                            <div className="file-icon">PDF</div>
                            <div className="file-info">
                                <div className="file-name">{doc.filename}</div>
                                <div className="file-meta">
                                    {formatFileSize(doc.file_size)} · {doc.page_count} 頁 · {formatDate(doc.created_at)}
                                </div>
                            </div>
                            {getStatusBadge(doc.status)}
                            <div className="file-actions">
                                {doc.status === 'completed' && (
                                    <button
                                        className="btn btn-success"
                                        onClick={() => handleDownload(doc)}
                                        style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                                    >
                                        📥 下載
                                    </button>
                                )}
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => handleDelete(doc)}
                                    style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                                >
                                    🗑️
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
