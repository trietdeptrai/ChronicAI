/**
 * Conversation sidebar — shared component for both doctor and patient chat.
 * Displays past conversations with titles, timestamps, and delete controls.
 */
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import type { ChatConversation } from "@/types"

interface ConversationSidebarProps {
    conversations: ChatConversation[]
    activeConversationId?: string
    isLoading?: boolean
    onSelect: (conversationId: string) => void
    onNewConversation: () => void
    onDelete: (conversationId: string) => void
}

function formatRelativeTime(dateStr: string): string {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return "Vừa xong"
    if (diffMins < 60) return `${diffMins} phút trước`
    if (diffHours < 24) return `${diffHours} giờ trước`
    if (diffDays < 7) return `${diffDays} ngày trước`
    return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })
}

export function ConversationSidebar({
    conversations,
    activeConversationId,
    isLoading = false,
    onSelect,
    onNewConversation,
    onDelete,
}: ConversationSidebarProps) {
    const [deletingId, setDeletingId] = useState<string | null>(null)

    const handleDelete = async (id: string) => {
        setDeletingId(id)
        try {
            await onDelete(id)
        } finally {
            setDeletingId(null)
        }
    }

    return (
        <div className="conversation-sidebar">
            <div className="sidebar-header">
                <h3 className="sidebar-title">Lịch sử hội thoại</h3>
                <Button
                    onClick={onNewConversation}
                    variant="outline"
                    size="sm"
                    className="new-chat-btn"
                >
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path
                            d="M8 3v10M3 8h10"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                        />
                    </svg>
                    Mới
                </Button>
            </div>

            <div className="sidebar-list" style={{ flex: 1, overflowY: "auto" }}>
                {isLoading ? (
                    <div className="sidebar-loading">
                        <div className="loading-spinner" />
                        <span>Đang tải...</span>
                    </div>
                ) : conversations.length === 0 ? (
                    <div className="sidebar-empty">
                        <p>Chưa có hội thoại nào</p>
                        <p className="sidebar-empty-hint">
                            Bắt đầu cuộc trò chuyện mới bằng cách gửi tin nhắn
                        </p>
                    </div>
                ) : (
                    <div className="conversation-list">
                        {conversations.map(conv => (
                            <div
                                key={conv.id}
                                className={`conversation-row ${deletingId === conv.id ? "deleting" : ""}`}
                            >
                                <button
                                    className={`conversation-item ${conv.id === activeConversationId ? "active" : ""}`}
                                    onClick={() => onSelect(conv.id)}
                                    disabled={deletingId === conv.id}
                                >
                                    <div className="conversation-item-content">
                                        <span className="conversation-title">
                                            {conv.title || "Hội thoại không tiêu đề"}
                                        </span>
                                        <span className="conversation-time">
                                            {formatRelativeTime(conv.updated_at)}
                                        </span>
                                    </div>
                                </button>
                                <button
                                    className="conversation-delete-btn"
                                    onClick={() => handleDelete(conv.id)}
                                    aria-label="Xóa hội thoại"
                                    disabled={deletingId === conv.id}
                                >
                                    <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 14 14"
                                        fill="none"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <path
                                            d="M2 4h10M5 4V3a1 1 0 011-1h2a1 1 0 011 1v1m1.5 0v7a1.5 1.5 0 01-1.5 1.5H5A1.5 1.5 0 013.5 11V4"
                                            stroke="currentColor"
                                            strokeWidth="1.2"
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                        />
                                    </svg>
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <style jsx>{`
                .conversation-sidebar {
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                    border-right: 1px solid hsl(var(--border));
                    background: hsl(var(--card));
                    width: 280px;
                    min-width: 280px;
                }

                .sidebar-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px;
                    border-bottom: 1px solid hsl(var(--border));
                }

                .sidebar-title {
                    font-size: 14px;
                    font-weight: 600;
                    color: hsl(var(--foreground));
                    margin: 0;
                }

                .new-chat-btn {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 13px;
                }

                .sidebar-loading,
                .sidebar-empty {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 32px 16px;
                    color: hsl(var(--muted-foreground));
                    text-align: center;
                }

                .loading-spinner {
                    width: 24px;
                    height: 24px;
                    border: 2px solid hsl(var(--border));
                    border-top-color: hsl(var(--primary));
                    border-radius: 50%;
                    animation: spin 0.6s linear infinite;
                    margin-bottom: 8px;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .sidebar-empty p {
                    margin: 0;
                    font-size: 13px;
                }

                .sidebar-empty-hint {
                    margin-top: 4px !important;
                    font-size: 12px !important;
                    opacity: 0.7;
                }

                .conversation-list {
                    display: flex;
                    flex-direction: column;
                    padding: 8px;
                    gap: 2px;
                }

                .conversation-row {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    border-radius: 8px;
                    padding-right: 4px;
                }

                .conversation-item {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    padding: 10px 12px;
                    border: none;
                    background: transparent;
                    border-radius: 8px;
                    cursor: pointer;
                    text-align: left;
                    transition: background-color 0.15s ease;
                    width: 0;
                    flex: 1;
                }

                .conversation-item:hover {
                    background: hsl(var(--accent));
                }

                .conversation-item.active {
                    background: hsl(var(--accent));
                    font-weight: 500;
                }

                .conversation-row.deleting {
                    opacity: 0.5;
                    pointer-events: none;
                }

                .conversation-item-content {
                    flex: 1;
                    min-width: 0;
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }

                .conversation-title {
                    font-size: 13px;
                    color: hsl(var(--foreground));
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    display: block;
                }

                .conversation-time {
                    font-size: 11px;
                    color: hsl(var(--muted-foreground));
                }

                .conversation-delete-btn {
                    flex-shrink: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 28px;
                    height: 28px;
                    border: none;
                    background: transparent;
                    border-radius: 6px;
                    cursor: pointer;
                    color: hsl(var(--muted-foreground));
                    opacity: 0;
                    transition: all 0.15s ease;
                }

                .conversation-row:hover .conversation-delete-btn {
                    opacity: 1;
                }

                .conversation-delete-btn:hover {
                    background: hsl(var(--destructive) / 0.1);
                    color: hsl(var(--destructive));
                }
            `}</style>
        </div>
    )
}
