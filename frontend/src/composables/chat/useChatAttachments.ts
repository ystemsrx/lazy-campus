import { ref, type Ref } from 'vue'

import { deleteAttachment, fetchAttachments, sendMessage, uploadAttachment } from '../../api/chat'
import { appConfirm } from '../../components/AppConfirm.vue'
import type { AppToastNotifier } from '../useAppToast'
import type { AttachmentCount, ChatAttachment, ChatMessage, Conversation } from '../../types/chat'
import { ATTACHMENT_MSG_PREFIX, getAttachmentFileName, getMessageAttachments, isAttachmentOnly } from './attachmentUtils'

interface UseChatAttachmentsOptions {
  activeConversation: Ref<Conversation | null>
  messages: Ref<ChatMessage[]>
  showToast: AppToastNotifier
  onAfterMessageAppended?: () => Promise<void> | void
}

export function useChatAttachments(options: UseChatAttachmentsOptions) {
  const showAttachmentModal = ref(false)
  const attachments = ref<ChatAttachment[]>([])
  const attachmentCount = ref<AttachmentCount>({ count: 0, limit: 5 })
  const uploadingFile = ref(false)

  async function loadAllAttachments() {
    if (!options.activeConversation.value) return

    try {
      attachments.value = await fetchAttachments(
        options.activeConversation.value.peer_id,
        options.activeConversation.value.task_id,
      )
      attachmentCount.value = { count: attachments.value.length, limit: 5 }
    } catch {
      // ignore
    }
  }

  async function openAttachmentModal() {
    if (!options.activeConversation.value) return
    showAttachmentModal.value = true
    await loadAllAttachments()
  }

  function resetAttachments() {
    attachments.value = []
    attachmentCount.value = { count: 0, limit: 5 }
  }

  async function handleFileUpload(event: Event) {
    const input = event.target as HTMLInputElement
    const files = input.files
    const activeConversation = options.activeConversation.value

    if (!files || files.length === 0 || !activeConversation) return

    const selectedFiles = Array.from(files)

    if (selectedFiles.length > 5) {
      options.showToast('一次最多选择 5 个文件', 'warning')
      input.value = ''
      return
    }

    const remaining = attachmentCount.value.limit - attachmentCount.value.count
    if (remaining <= 0) {
      options.showToast(`每个会话最多上传 ${attachmentCount.value.limit} 个附件，请先删除已有附件`, 'warning')
      input.value = ''
      return
    }

    const toUpload = selectedFiles.slice(0, remaining).filter((file) => {
      if (file.size > 10 * 1024 * 1024) {
        options.showToast(`「${file.name}」超过 10 MB，已跳过`, 'error')
        return false
      }
      return true
    })

    if (toUpload.length === 0) {
      input.value = ''
      return
    }

    if (selectedFiles.length > remaining) {
      options.showToast(`附件剩余配额 ${remaining} 个，已自动截取前 ${toUpload.length} 个文件`, 'warning')
    }

    uploadingFile.value = true

    try {
      const fileNames = toUpload.map((file) => file.name).join('、')
      const messageContent =
        toUpload.length === 1
          ? `${ATTACHMENT_MSG_PREFIX} ${toUpload[0].name}`
          : `${ATTACHMENT_MSG_PREFIX} ${fileNames}（共 ${toUpload.length} 个文件）`

      const message = await sendMessage(activeConversation.peer_id, messageContent, activeConversation.task_id)
      options.messages.value.push(message)
      await options.onAfterMessageAppended?.()

      const results = await Promise.allSettled(
        toUpload.map((file) => uploadAttachment(activeConversation.peer_id, file, activeConversation.task_id, message.id)),
      )

      for (const result of results) {
        if (result.status === 'fulfilled') {
          attachments.value.unshift(result.value)
          attachmentCount.value.count++
        }
      }

      const failCount = results.filter((result) => result.status === 'rejected').length
      if (failCount > 0) {
        options.showToast(`${failCount} 个文件上传失败`, 'error')
      }
    } catch (error: any) {
      options.showToast(error?.response?.data?.detail || '上传失败', 'error')
    }

    uploadingFile.value = false
    input.value = ''
  }

  async function handleDeleteAttachment(attachment: ChatAttachment) {
    const confirmed = await appConfirm({
      title: '删除附件',
      message: `确定删除附件「${attachment.file_name}」吗？删除后不可恢复。`,
      confirmText: '删除',
      type: 'danger',
    })

    if (!confirmed) return

    try {
      await deleteAttachment(attachment.id)
      attachments.value = attachments.value.filter((item) => item.id !== attachment.id)
      attachmentCount.value.count--
      options.showToast('附件已删除', 'success')
    } catch {
      // ignore
    }
  }

  return {
    showAttachmentModal,
    attachments,
    attachmentCount,
    uploadingFile,
    loadAllAttachments,
    openAttachmentModal,
    resetAttachments,
    handleFileUpload,
    handleDeleteAttachment,
    isAttachmentOnly,
    getAttachmentFileName,
    getMessageAttachments,
  }
}
