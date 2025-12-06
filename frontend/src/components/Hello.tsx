interface HelloProps {
  name?: string
}

export function Hello({ name = 'World' }: HelloProps) {
  return <div>Hello, {name}</div>
}
