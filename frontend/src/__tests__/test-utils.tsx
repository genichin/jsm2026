import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'

// 필요한 Provider들을 여기에 추가할 수 있습니다
// 예: QueryClientProvider, AuthProvider 등
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>
}

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

export * from '@testing-library/react'
export { customRender as render }
