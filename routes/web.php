<?php

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| contains the "web" middleware group. Now create something great!
|
*/

// Home
Route::get('/', 'HomeController@index')->name('home');

// Authentication and accounts
Auth::routes(['verify' => true]);
Route::get('/account', 'UserController@edit')->name('accounts.edit')->middleware('verified');
Route::patch('/account', 'UserController@update')->name('accounts.update')->middleware('verified');

// API's
Route::resource('/api/towers', 'TowerController');

// Boards
Route::get('/boards/search', 'BoardController@search')->name('boards.search');
Route::resource('/boards', 'BoardController');
Route::get('/boards/{board}/archive', 'BoardController@archive')->name('boards.archive');
Route::get('/boards/{board}/committee', 'BoardController@committee')->name('boards.committee');
Route::get('/boards/{board}/details', 'BoardController@details')->name('boards.details');
Route::get('/boards/{board}/contact', 'BoardController@contact')->name('boards.contact');
Route::post('/boards/{board}/contact', 'BoardController@contactSend')
       ->name('boards.contact.send')
       ->middleware('verified');
Route::get('/boards/{board}/members', 'BoardController@members')->name('boards.members');
Route::get('/boards/{board}/members/add', 'BoardController@addMembers')->name('boards.members.add');
Route::get('/boards/{board}/subscribe', 'BoardController@subscribe')->name('boards.subscribe');

// Notices
Route::resource('/boards/{board}/notices', 'BoardNoticeController');
Route::delete('/boards/{board}/notices/{notice}/archive', 'BoardNoticeController@archive')->name('notices.archive');
Route::post('/boards/{board}/notices/{notice}/archive', 'BoardNoticeController@unarchive')->name('notices.unarchive');
Route::post('/boards/{board}/notices/{notice}/reply', 'BoardNoticeController@reply')->name('notices.reply');
Route::resource('/boards/{board}/notices/{notice}/messages', 'NoticeMessageController');

Route::get('/boards/{board}/notices/{notice}/mail/created', 'BoardNoticeController@showNoticeMail');

// Subscription
Route::post('/boards/{board}/subscriptions/users/{user?}', 'SubscriptionController@store')->name('subscriptions.store');
Route::match(['get', 'delete'], '/boards/{board}/subscriptions/users/{user?}', 'SubscriptionController@destroy')
    ->name('subscriptions.destroy');
Route::patch('/boards/{board}/subscriptions/users/{user?}', 'SubscriptionController@update')
    ->name('subscriptions.update');
Route::post('/boards/{board}/subscriptions/email', 'SubscriptionController@bulkAdd')->name('subscriptions.bulk');
Route::get('/boards/{board}/subscriptions/email/{email}', 'SubscriptionController@add')->name('subscriptions.add');
Route::post('/boards/{board}/subscriptions/link', 'SubscriptionController@sendLink')->name('subscriptions.link');

// Roles
Route::resource('/boards/{board}/roles', 'BoardRoleController');
