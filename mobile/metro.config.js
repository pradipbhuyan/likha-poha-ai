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

module.exports = config;
