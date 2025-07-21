import { Header } from '@/components/layout/header'
import { WorkspaceContainer } from '@/components/workspace/workspace-container'
import { WorkspaceSidebar } from '@/components/workspace/workspace-sidebar'
import { WorkspaceContent } from '@/components/workspace/workspace-content'

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <WorkspaceContainer>
        <WorkspaceSidebar />
        <WorkspaceContent />
      </WorkspaceContainer>
    </div>
  )
}