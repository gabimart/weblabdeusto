/*
* Copyright (C) 2005 onwards University of Deusto
* All rights reserved.
*
* This software is licensed as described in the file COPYING, which
* you should have received as part of this distribution.
*
* This software consists of contributions made by many individuals, 
* listed below:
*
* Author: Pablo Orduña <pablo@ordunya.com>
*
*/ 
package es.deusto.weblab.client.comm.callbacks;

import es.deusto.weblab.client.dto.SessionID;

public interface ISessionIdCallback extends IWebLabAsyncCallback{	
	public void onSuccess(SessionID sessionId);
	//throws WlCommException, LoginException, InvalidUserOrPasswordException
}
