'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Template {
    id: number;
    name: string;
    description: string;
    page_count: number;
    created_at: string;
}

interface UploadedFile {
    id: number;
    filename: string;
    file_size: number;
    page_count: number;
    status: string;
}

type Step = 'template' | 'thesis' | 'processing';

export default function UploadPage() {
    const [currentStep, setCurrentStep] = useState<Step>('template');
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);

    // 範本相關狀態
    const [templates, setTemplates] = useState<Template[]>([]);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [templateName, setTemplateName] = useState('');

    // 論文相關狀態
    const [uploadedThesis, setUploadedThesis] = useState<UploadedFile | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

    // 載入已有的範本
    useEffect(() => {
        fetchTemplates();
    }, []);

    const fetchTemplates = async () => {
        try {
            const response = await fetch('/api/templates');
            if (response.ok) {
                const data = await response.json();
                setTemplates(data.templates || []);
            }
        } catch (err) {
            console.error('載入範本失敗:', err);
        }
    };

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }, [currentStep]);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    }, [currentStep]);

    const handleFile = async (file: File) => {
        // 驗證文件類型
        const ext = file.name.toLowerCase();
        if (!ext.endsWith('.pdf') && !ext.endsWith('.docx') && !ext.endsWith('.doc')) {
            setError('只支援 PDF 和 Word (.docx) 格式的文件');
            return;
        }

        // 驗證文件大小（最大 50MB）
        if (file.size > 50 * 1024 * 1024) {
            setError('文件大小不能超過 50MB');
            return;
        }

        setError(null);
        setIsUploading(true);
        setUploadProgress(0);

        const formData = new FormData();
        formData.append('file', file);

        try {
            // 模擬上傳進度
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => {
                    if (prev >= 90) {
                        clearInterval(progressInterval);
                        return prev;
                    }
                    return prev + 10;
                });
            }, 200);

            let response;

            if (currentStep === 'template') {
                // 上傳範本
                const url = `/api/templates/upload?name=${encodeURIComponent(templateName || '我的範本')}`;
                response = await fetch(url, {
                    method: 'POST',
                    body: formData,
                });
            } else {
                // 上傳論文
                response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData,
                });
            }

            clearInterval(progressInterval);
            setUploadProgress(100);

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || '上傳失敗');
            }

            const data = await response.json();

            if (currentStep === 'template') {
                // 範本上傳成功
                await fetchTemplates();
                setSelectedTemplate({
                    id: data.id,
                    name: data.name,
                    description: data.description,
                    page_count: data.page_count,
                    created_at: new Date().toISOString()
                });
                setCurrentStep('thesis');
            } else {
                // 論文上傳成功
                setUploadedThesis(data);
            }

            setIsUploading(false);

        } catch (err) {
            setError(err instanceof Error ? err.message : '上傳失敗，請稍後再試');
            setIsUploading(false);
            setUploadProgress(0);
        }
    };

    const handleApplyTemplate = async () => {
        if (!uploadedThesis || !selectedTemplate) return;

        setIsProcessing(true);
        setCurrentStep('processing');
        setError(null);

        try {
            const response = await fetch(
                `/api/documents/${uploadedThesis.id}/apply-template/${selectedTemplate.id}`,
                { method: 'POST' }
            );

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || '處理失敗');
            }

            // 導航到文件列表頁面
            router.push('/documents');

        } catch (err) {
            setError(err instanceof Error ? err.message : '處理失敗，請稍後再試');
            setIsProcessing(false);
            setCurrentStep('thesis');
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const renderStepIndicator = () => (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '1rem',
            marginBottom: '2rem'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: currentStep === 'template' ? 1 : 0.5
            }}>
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: currentStep === 'template' ? 'var(--gradient-primary)' :
                        (currentStep !== 'template' ? 'var(--success-500)' : 'var(--gray-300)'),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold'
                }}>
                    {currentStep !== 'template' ? '✓' : '1'}
                </div>
                <span>上傳範本</span>
            </div>

            <div style={{ width: '40px', height: '2px', background: 'var(--gray-300)', margin: 'auto 0' }} />

            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: currentStep === 'thesis' ? 1 : 0.5
            }}>
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: currentStep === 'thesis' ? 'var(--gradient-primary)' :
                        (currentStep === 'processing' ? 'var(--success-500)' : 'var(--gray-300)'),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold'
                }}>
                    {currentStep === 'processing' ? '✓' : '2'}
                </div>
                <span>上傳論文</span>
            </div>

            <div style={{ width: '40px', height: '2px', background: 'var(--gray-300)', margin: 'auto 0' }} />

            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: currentStep === 'processing' ? 1 : 0.5
            }}>
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: currentStep === 'processing' ? 'var(--gradient-primary)' : 'var(--gray-300)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold'
                }}>3</div>
                <span>格式調整</span>
            </div>
        </div>
    );

    return (
        <div className="container" style={{ maxWidth: '800px', padding: '2rem 1.5rem' }}>
            <h1 className="text-center mb-6">論文格式調整</h1>

            {renderStepIndicator()}

            {/* 錯誤訊息 */}
            {error && (
                <div style={{
                    padding: '1rem',
                    background: 'var(--error-500)',
                    color: 'white',
                    borderRadius: 'var(--radius)',
                    marginBottom: '1.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                }}>
                    ⚠️ {error}
                </div>
            )}

            {/* 步驟 1: 上傳範本 */}
            {currentStep === 'template' && (
                <div className="card animate-fade-in">
                    <h3 className="mb-4">📄 步驟 1：上傳格式範本</h3>
                    <p style={{ color: 'var(--gray-500)', marginBottom: '1.5rem' }}>
                        請上傳一份具有您想要格式的 PDF 文件（例如：學校提供的論文範例）
                    </p>

                    {/* 範本名稱輸入 */}
                    <div className="mb-4">
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                            範本名稱
                        </label>
                        <input
                            type="text"
                            value={templateName}
                            onChange={(e) => setTemplateName(e.target.value)}
                            placeholder="例如：學校論文格式"
                            style={{
                                width: '100%',
                                padding: '0.75rem 1rem',
                                border: '1px solid var(--gray-300)',
                                borderRadius: 'var(--radius)',
                                fontSize: '1rem'
                            }}
                        />
                    </div>

                    {/* 已有範本選擇 */}
                    {templates.length > 0 && (
                        <div className="mb-4">
                            <h4 style={{ marginBottom: '0.75rem' }}>或選擇已有的範本：</h4>
                            <div className="template-grid">
                                {templates.map((t) => (
                                    <div
                                        key={t.id}
                                        className={`template-card ${selectedTemplate?.id === t.id ? 'selected' : ''}`}
                                        onClick={() => {
                                            setSelectedTemplate(t);
                                            setCurrentStep('thesis');
                                        }}
                                    >
                                        <div className="template-name">📚 {t.name}</div>
                                        <div className="template-description">{t.description}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 上傳區域 */}
                    <div
                        className={`upload-zone ${isDragging ? 'drag-over' : ''}`}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf,.docx,.doc"
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                        />

                        {isUploading ? (
                            <div>
                                <div className="upload-icon animate-spin">📤</div>
                                <h3 className="upload-title">正在上傳並學習格式...</h3>
                                <div className="progress-bar" style={{ maxWidth: '300px', margin: '1rem auto' }}>
                                    <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                                </div>
                            </div>
                        ) : (
                            <div>
                                <div className="upload-icon">📄</div>
                                <h3 className="upload-title">上傳格式範本</h3>
                                <p className="upload-subtitle">支援 PDF 或 Word (.docx)</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 步驟 2: 上傳論文 */}
            {currentStep === 'thesis' && selectedTemplate && (
                <div className="card animate-fade-in">
                    <h3 className="mb-4">📝 步驟 2：上傳您的論文</h3>

                    {/* 已選範本資訊 */}
                    <div style={{
                        padding: '1rem',
                        background: 'var(--primary-50)',
                        borderRadius: 'var(--radius)',
                        marginBottom: '1.5rem'
                    }}>
                        <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                            已選擇範本：{selectedTemplate.name}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>
                            {selectedTemplate.description}
                        </div>
                    </div>

                    {!uploadedThesis ? (
                        <div
                            className={`upload-zone ${isDragging ? 'drag-over' : ''}`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.docx,.doc"
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                            />

                            {isUploading ? (
                                <div>
                                    <div className="upload-icon animate-spin">📤</div>
                                    <h3 className="upload-title">正在上傳論文...</h3>
                                    <div className="progress-bar" style={{ maxWidth: '300px', margin: '1rem auto' }}>
                                        <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <div className="upload-icon">📝</div>
                                    <h3 className="upload-title">上傳您的論文</h3>
                                    <p className="upload-subtitle">支援 PDF 或 Word (.docx)</p>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div>
                            {/* 論文資訊 */}
                            <div className="file-item" style={{ marginBottom: '1.5rem' }}>
                                <div className="file-icon">{uploadedThesis.filename.toLowerCase().endsWith('.pdf') ? 'PDF' : 'DOCX'}</div>
                                <div className="file-info">
                                    <div className="file-name">{uploadedThesis.filename}</div>
                                    <div className="file-meta">
                                        {formatFileSize(uploadedThesis.file_size)} · {uploadedThesis.page_count} 頁
                                    </div>
                                </div>
                                <span className="status-badge status-uploaded">已上傳</span>
                            </div>

                            {/* 操作按鈕 */}
                            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => {
                                        setUploadedThesis(null);
                                        setUploadProgress(0);
                                    }}
                                >
                                    重新上傳
                                </button>
                                <button
                                    className="btn btn-primary"
                                    onClick={handleApplyTemplate}
                                    disabled={isProcessing}
                                >
                                    {isProcessing ? '處理中...' : '開始套用格式 →'}
                                </button>
                            </div>
                        </div>
                    )}

                    <button
                        className="btn btn-secondary mt-4"
                        onClick={() => {
                            setCurrentStep('template');
                            setSelectedTemplate(null);
                        }}
                        style={{ width: '100%' }}
                    >
                        ← 返回選擇範本
                    </button>
                </div>
            )}

            {/* 步驟 3: 處理中 */}
            {currentStep === 'processing' && (
                <div className="card animate-fade-in text-center" style={{ padding: '3rem 2rem' }}>
                    <div style={{ fontSize: '4rem' }} className="animate-spin">⚙️</div>
                    <h3 className="mt-4">正在套用格式...</h3>
                    <p style={{ color: 'var(--gray-500)' }}>
                        系統正在根據範本調整您的論文格式，請稍候
                    </p>
                </div>
            )}
        </div>
    );
}
