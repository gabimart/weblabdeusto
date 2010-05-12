/*
* Copyright (C) 2005-2009 University of Deusto
* All rights reserved.
*
* This software is licensed as described in the file COPYING, which
* you should have received as part of this distribution.
*
* This software consists of contributions made by many individuals, 
* listed below:
*
* Author: FILLME
*
*/

package es.deusto.weblab.client.admin.ui;

import com.google.gwt.core.client.GWT;
import com.google.gwt.core.client.RunAsyncCallback;

import es.deusto.weblab.client.admin.controller.IWlAdminController;
import es.deusto.weblab.client.admin.ui.themes.es.deusto.weblab.defaultweb.DefaultTheme;
import es.deusto.weblab.client.configuration.IConfigurationManager;
import es.deusto.weblab.client.ui.exceptions.themes.ThemeNotFoundException;

public class WlAdminThemeFactory {
	
	public interface IWlAdminThemeLoadedCallback{
		public void onThemeLoaded(WlAdminThemeBase theme);
		public void onFailure(Throwable reason);
	}
	
	public static void themeFactory(final IConfigurationManager configurationManager, final IWlAdminController controller, String themeName, final IWlAdminThemeLoadedCallback callback){
		if(themeName.equals("deusto")){
			GWT.runAsync(new RunAsyncCallback() {
				@Override
				public void onSuccess() {
					final WlAdminThemeBase themeBase = new DefaultTheme(configurationManager, controller);
					callback.onThemeLoaded(themeBase);
				}
				@Override
				public void onFailure(Throwable reason) {}
			});
		}else
			callback.onFailure(new ThemeNotFoundException("Theme " + themeName + " not found"));
	}	
}
