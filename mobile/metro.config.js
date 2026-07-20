// Learn more https://docs.expo.dev/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const sharedRoot = path.resolve(projectRoot, '..', 'shared');

const config = getDefaultConfig(projectRoot);

// Allow importing the monorepo's shared/ package (subscription/subject-access
// logic used by both web and mobile). Not a formal npm/yarn workspace, so
// Metro needs to be told explicitly to watch and resolve it.
config.watchFolders = [...(config.watchFolders || []), sharedRoot];
config.resolver.extraNodeModules = {
  ...(config.resolver.extraNodeModules || {}),
  '@likhapoha/shared': sharedRoot,
};

// Custom resolver to handle @likhapoha/shared/* subpath imports.
// extraNodeModules handles the package root but Metro may not automatically
// resolve subpaths like @likhapoha/shared/utils/subjectAccess, so we
// intercept them explicitly here.
const originalResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName.startsWith('@likhapoha/shared/')) {
    const subpath = moduleName.slice('@likhapoha/shared/'.length);
    const resolved = path.resolve(sharedRoot, subpath);
    return { type: 'sourceFile', filePath: resolved + '.js' };
  }
  if (originalResolveRequest) {
    return originalResolveRequest(context, moduleName, platform);
  }
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
