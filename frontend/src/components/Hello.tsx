interface HelloProps {
  name?: string;
}

export function Hello({ name = 'World' }: HelloProps) {
  return <p>Hello, {name}</p>;
}
