export interface DemoProject {
  id: string;
  number: string | number;
  type: string;
  title: string;
  name?: string;
  status: string;
  progress: number;
  updated?: string;
  user?: string;
  created?: string;
  editor?: string;
}

export const DEMO_PROJECTS: DemoProject[] = [
  {
    id: "123e-ac-101",
    number: "AC-101",
    type: "Advisory Circular",
    title: "Policy Update",
    name: "Policy Update",
    status: "In Progress",
    progress: 40,
    updated: "2025-07-04",
    user: "Jane Doe",
  },
  {
    id: "123e-ac-102",
    number: "AC-102",
    type: "Order",
    title: "Compliance Review",
    name: "Compliance Review",
    status: "Complete",
    progress: 100,
    updated: "2025-07-02",
    user: "Jane Doe",
  },
  {
    id: "123e-ac-103",
    number: "AC-103",
    type: "SOP",
    title: "Draft SOP",
    name: "Draft SOP",
    status: "Draft",
    progress: 10,
    updated: "2025-07-01",
    user: "Jane Doe",
  },
  {
    id: "123e-ac-104",
    number: "AC-104",
    type: "Incident Report",
    title: "Incident Report",
    name: "Incident Report",
    status: "Review",
    progress: 70,
    updated: "2025-07-03",
    user: "Jane Doe",
  },
];

export function getDemoProject(id: string): DemoProject | undefined {
  return DEMO_PROJECTS.find((p) => p.id === id);
}
