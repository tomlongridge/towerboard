<?php

namespace App\Http\Controllers;

use Auth;
use DB;

use App\Notice;

class UserNoticeController extends Controller
{
    public function index()
    {
        if (Auth::check()) {
            $notices = Auth::user()->notices()
                           ->orderBy('created_at', 'desc')->get()
                           ->groupBy(function ($notice) {
                               return $notice->created_at->toDateString();
                           });
            return view('notices.index', compact('notices'));
        } else {
            return view('welcome');
        }
    }
}
