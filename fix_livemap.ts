import { Project, SyntaxKind, Node } from "ts-morph";

const project = new Project();
project.addSourceFileAtPath("admin-dashboard/src/pages/LiveMap.tsx");
const sourceFile = project.getSourceFileOrThrow("admin-dashboard/src/pages/LiveMap.tsx");

// Find all functions inside AdminLiveMap and extract them if possible, or just break down complex functions.
// Actually, doing this via script is hard to get right. Let's just create a simpler file by copying and replacing.
