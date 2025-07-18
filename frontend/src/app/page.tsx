import { Header } from '@/components/layout/header'
import { MainContent } from '@/components/layout/main-content'

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <MainContent />
    </div>
  )
}